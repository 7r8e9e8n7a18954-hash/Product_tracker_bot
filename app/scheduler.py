from apscheduler.schedulers.asyncio import AsyncIOScheduler

def build_scheduler(interval_minutes: int, async_check_callback):
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        async_check_callback,
        trigger="interval",
        minutes=interval_minutes,
        id="product_price_checks",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
