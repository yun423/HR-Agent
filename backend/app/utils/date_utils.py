""""""
from datetime import datetime, timezone, timedelta
from typing import Optional
import pytz


"""
    date_utils.py是日期时间工具函数集合。不直接处理业务数据库，是给项目其他模块提供通用的时间计算、格式化、解析、时区转换和展示文本能力。

    这个文件就是项目的日期时间工具箱。
        我们把常见的时间处理逻辑集中起来，避免业务代码里到处重复写格式化、时区转换、时间差计算、日期边界计算等代码。
"""



def utc_now() -> datetime:
    """
        返回当前 UTC 时间
            返回的是带时区信息的datetime。项目里如果需要统一存储或比较时间，UTC是比较稳妥的基准。
    """
    return datetime.now(timezone.utc)


def format_datetime(
    dt: datetime,
    format_string: str = "%Y-%m-%d %H:%M:%S",
    timezone_name: Optional[str] = None
) -> str:
    """
        把datetime转成字符串
    """
    if not dt:
        return ""

    # 如果传了timezone_name, 会把时间转换到对应timezone_name的时区，再格式化。
    # 如果时区转换失败，就直接使用原始时间，避免函数报错影响业务流程。
    if timezone_name:
        try:
            tz = pytz.timezone(timezone_name)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(tz)
        except Exception:
            pass

    return dt.strftime(format_string)


def parse_datetime(
    date_string: str,
    format_string: str = "%Y-%m-%d %H:%M:%S",
    timezone_name: Optional[str] = None
) -> Optional[datetime]:
    """
        它把字符串解析成datetime
    """
    if not date_string:
        return None

    try:
        dt = datetime.strptime(date_string, format_string)

        # 如果传了timezone_name，会把解析出来的datetime标记成本地化时区。
        # 如果没传时区，且解析结果没有时区信息，就默认设置为UTC。
        # 解析失败时返回None，不会抛异常。
        if timezone_name:
            try:
                tz = pytz.timezone(timezone_name)
                dt = tz.localize(dt)
            except Exception:
                dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt
    except ValueError:
        return None


def get_timezone(timezone_name: str) -> Optional[timezone]:
    """
        根据时区名称返回pytz时区对象
        如果名称非法，返回None。
    """
    try:
        return pytz.timezone(timezone_name)
    except Exception:
        return None


def days_between(start_date: datetime, end_date: datetime) -> int:
    """
        计算两个时间之间相差多少天
    """
    if not start_date or not end_date:
        return 0

    if start_date.tzinfo is None and end_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    elif start_date.tzinfo is not None and end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    delta = end_date - start_date
    return delta.days


def hours_between(start_time: datetime, end_time: datetime) -> float:
    """
        计算两个时间之间相差多少小时，返回浮点数。
    """
    if not start_time or not end_time:
        return 0.0

    if start_time.tzinfo is None and end_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    elif start_time.tzinfo is not None and end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    delta = end_time - start_time
    return delta.total_seconds() / 3600


def add_days(dt: datetime, days: int) -> datetime:
    """
        时间加法：添加天数
    """
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """
        时间加法：添加小时
    """
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
        时间加法：添加分钟
    """
    return dt + timedelta(minutes=minutes)


def start_of_day(dt: datetime) -> datetime:
    """
        返回当天 00:00:00
    """
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime) -> datetime:
    """
        返回当天 23:59:59.999999。
    """
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def start_of_week(dt: datetime) -> datetime:
    """
        返回本周一的开始时间。
    """
    days_since_monday = dt.weekday()
    monday = dt - timedelta(days=days_since_monday)
    return start_of_day(monday)


def end_of_week(dt: datetime) -> datetime:
    """
        返回本周日的结束时间。
    """
    days_until_sunday = 6 - dt.weekday()
    sunday = dt + timedelta(days=days_until_sunday)
    return end_of_day(sunday)


def start_of_month(dt: datetime) -> datetime:
    """
        返回本月第一天的开始时间。
    """
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def end_of_month(dt: datetime) -> datetime:
    """
        返回本月最后一天的结束时间:
            做法是：先得到下个月第一天，再减一天。
    """
    if dt.month == 12:
        next_month = dt.replace(year=dt.year + 1, month=1, day=1)
    else:
        next_month = dt.replace(month=dt.month + 1, day=1)

    last_day = next_month - timedelta(days=1)
    return end_of_day(last_day)


def is_weekend(dt: datetime) -> bool:
    """ 判断是否周末 """
    return dt.weekday() >= 5


def is_business_day(dt: datetime) -> bool:
    """ 判断是否工作日，也就是周一到周五 """
    return dt.weekday() < 5


def get_age_in_years(birth_date: datetime, reference_date: Optional[datetime] = None) -> int:
    """
        根据出生日期计算年龄
            1. 先用年份相减。
            2. 如果今年生日还没到，就减1。
            3. 最后用max(0, age)避免返回负数。
        可以用于简历、候选人资料等场景。
    """
    if not birth_date:
        return 0

    if reference_date is None:
        reference_date = utc_now()

    age = reference_date.year - birth_date.year

    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    return max(0, age)


def format_duration(seconds: float) -> str:
    """
        把秒数 转换成 可读文本:
            可以用于接口耗时、任务执行时长展示。
    """
    if seconds < 0:
        return "0 seconds"

    if seconds < 60:
        return f"{seconds:.1f} seconds"

    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"

    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f} hours"

    days = hours / 24
    return f"{days:.1f} days"


def get_relative_time(dt: datetime, reference_time: Optional[datetime] = None) -> str:
    """
        返回类似这样的文本 ('2 hours ago', 'in 3 days', 'now')
            单位会根据差值自动选择 seconds、minutes、hours、days、months、years。
    """
    if not dt:
        return "unknown"

    if reference_time is None:
        reference_time = utc_now()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    delta = dt - reference_time
    total_seconds = delta.total_seconds()

    if total_seconds == 0:
        return "now"

    future = total_seconds > 0
    total_seconds = abs(total_seconds)

    if total_seconds < 60:
        unit = "second" if total_seconds == 1 else "seconds"
        value = int(total_seconds)
    elif total_seconds < 3600:  # < 1 hour
        value = int(total_seconds / 60)
        unit = "minute" if value == 1 else "minutes"
    elif total_seconds < 86400:  # < 1 day
        value = int(total_seconds / 3600)
        unit = "hour" if value == 1 else "hours"
    elif total_seconds < 2592000:  # < 30 days
        value = int(total_seconds / 86400)
        unit = "day" if value == 1 else "days"
    elif total_seconds < 31536000:  # < 1 year
        value = int(total_seconds / 2592000)
        unit = "month" if value == 1 else "months"
    else:
        value = int(total_seconds / 31536000)
        unit = "year" if value == 1 else "years"

    if future:
        return f"in {value} {unit}"
    else:
        return f"{value} {unit} ago"


def convert_timezone(dt: datetime, from_tz: str, to_tz: str) -> Optional[datetime]:
    """
        把一个时间从一个时区转换到另一个时区
    """
    try:
        from_timezone = pytz.timezone(from_tz)
        to_timezone = pytz.timezone(to_tz)

        # 如果传入的dt没有时区信息，它会先按from_tz本地化，然后再转到to_tz
        if dt.tzinfo is None:
            dt = from_timezone.localize(dt)

        return dt.astimezone(to_timezone)
    except Exception:
        return None


def get_common_timezones() -> list[str]:
    """
        返回一组常用时区名称
    """
    return [
        'UTC',
        'US/Eastern',
        'US/Central',
        'US/Mountain',
        'US/Pacific',
        'Europe/London',
        'Europe/Paris',
        'Europe/Berlin',
        'Asia/Tokyo',
        'Asia/Shanghai',
        'Asia/Kolkata',
        'Australia/Sydney',
        'America/New_York',
        'America/Chicago',
        'America/Denver',
        'America/Los_Angeles',
    ]


