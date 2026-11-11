"""
轻量邮件抓取调度器：
    基于 asyncio 为每个邮箱配置启动后台任务，按 fetch_interval 周期抓取邮件附件。
    支持启动、停止、刷新某个邮箱配置对应的任务，也能在 shutdown 时清理所有任务。
"""
import asyncio
import re
from typing import Dict
from app.core.database import AsyncSessionLocal
from app.models.email_config import EmailConfig
from app.services.email_service import EmailConfigService, EmailFetchService


class EmailScheduler:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.stoppers: Dict[str, asyncio.Event] = {}

    async def start(self):
        async with AsyncSessionLocal() as db:
            svc = EmailConfigService(db)
            configs = await svc.list(skip=0, limit=1000)
        # 为自动抓取配置调度任务
        for cfg in configs:
            if getattr(cfg, "auto_fetch", False) and getattr(cfg, "status", "active") == "active":
                interval_min = max(1, int(getattr(cfg, "fetch_interval", 30) or 30))
                stopper = asyncio.Event()
                self.stoppers[str(cfg.id)] = stopper
                task = asyncio.create_task(self._run_fetch_loop(str(cfg.id), interval_min, stopper))
                self.tasks[str(cfg.id)] = task

    async def _run_fetch_loop(self, config_id: str, interval_min: int, stopper: asyncio.Event):
        while not stopper.is_set():
            try:
                async with AsyncSessionLocal() as db:
                    cfg_svc = EmailConfigService(db)
                    fetch_svc = EmailFetchService(db)
                    cfg = await cfg_svc.get(config_id)
                    if cfg and getattr(cfg, "auto_fetch", False) and getattr(cfg, "status", "active") == "active":
                        # 从配置中解析主题关键词，支持全角/半角逗号分隔
                        raw = (getattr(cfg, 'subject_keywords', '') or '').strip()
                        print('subject_keywords:',raw)
                        if raw:
                            parts = [p.strip() for p in re.split(r"[,，]", raw) if p.strip()]
                            kws = parts if parts else ['简历']
                        else:
                            kws = ['简历','招聘','岗位','职位']
                        log = await fetch_svc.fetch_recent_attachments(cfg, cfg.created_by, limit=10, subject_keyword=kws)
                        await db.commit()
            except Exception:
                # 忽略错误并继续执行
                pass
            # 休眠间隔时间
            try:
                await asyncio.wait_for(stopper.wait(), timeout=interval_min * 60)
            except asyncio.TimeoutError:
                continue

    async def shutdown(self):
        for stopper in self.stoppers.values():
            stopper.set()
        for task in self.tasks.values():
            try:
                task.cancel()
            except Exception:
                pass
        self.tasks.clear()
        self.stoppers.clear()

    async def stop_task_for_config(self, config_id: str):
        stopper = self.stoppers.get(config_id)
        if stopper:
            stopper.set()
        task = self.tasks.get(config_id)
        if task:
            try:
                task.cancel()
            except Exception:
                pass
        self.tasks.pop(config_id, None)
        self.stoppers.pop(config_id, None)

    async def start_task_for_config(self, config_id: str, interval_min: int):
        await self.stop_task_for_config(config_id)
        stopper = asyncio.Event()
        self.stoppers[config_id] = stopper
        task = asyncio.create_task(self._run_fetch_loop(config_id, interval_min, stopper))
        self.tasks[config_id] = task

    async def refresh_for_config(self, config: EmailConfig):
        cfg_id = str(config.id)
        await self.stop_task_for_config(cfg_id)
        if getattr(config, "auto_fetch", False) and getattr(config, "status", "active") == "active":
            interval_min = max(1, int(getattr(config, "fetch_interval", 30) or 30))
            print('interval_min:%s' % interval_min)
            await self.start_task_for_config(cfg_id, interval_min)
