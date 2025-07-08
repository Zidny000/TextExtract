"""
Background job scheduler for handling subscription checks and other tasks.
"""
import logging
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database.models import Subscription

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(daemon=True)

def check_expired_subscriptions():
    """
    Background job to check for expired subscriptions and update their status.
    This runs daily to ensure that subscriptions that have passed their end date
    are properly marked as expired in the database.
    """
    try:
        logger.info("Running scheduled job: check_expired_subscriptions")
        
        # Get the current time in UTC
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Get all active subscriptions
        active_subscriptions = Subscription.get_all_active_subscriptions()
        
        update_count = 0
        for subscription in active_subscriptions:
            # Skip subscriptions without an end date
            if not subscription.get("end_date"):
                continue
                
            try:
                # Parse the end date
                end_date = datetime.datetime.fromisoformat(
                    subscription["end_date"].replace("Z", "+00:00")
                )
                
                # Check if the subscription has expired
                if end_date < now:
                    # Update subscription status to expired
                    Subscription.update_status(subscription["id"], "expired")
                    logger.info(f"Marked subscription {subscription['id']} as expired (ended: {end_date})")
                    update_count += 1
            except Exception as sub_err:
                logger.error(f"Error processing subscription {subscription['id']}: {str(sub_err)}")
                
        logger.info(f"Completed check_expired_subscriptions: {update_count} subscriptions marked as expired")
    except Exception as e:
        logger.error(f"Error in check_expired_subscriptions job: {str(e)}")

def check_subscription_renewals():
    """
    Background job to check for subscriptions that need to be renewed.
    This tries to auto-renew subscriptions that are about to expire.
    """
    try:
        logger.info("Running scheduled job: check_subscription_renewals")
        
        # Get all active subscriptions with auto-renewal enabled
        active_subscriptions = Subscription.get_all_active_subscriptions()
        
        renewal_count = 0
        for subscription in active_subscriptions:
            # Skip subscriptions without auto-renewal
            if not subscription.get("auto_renewal", False):
                continue
                
            try:
                # Try to renew if needed
                if Subscription.check_renewal(subscription["id"]):
                    renewal_count += 1
            except Exception as sub_err:
                logger.error(f"Error processing renewal for subscription {subscription['id']}: {str(sub_err)}")
                
        logger.info(f"Completed check_subscription_renewals: {renewal_count} subscriptions renewed")
    except Exception as e:
        logger.error(f"Error in check_subscription_renewals job: {str(e)}")

def init_scheduler():
    """Initialize the scheduler with all background jobs"""
    # Add jobs to the scheduler
    scheduler.add_job(check_expired_subscriptions, 'cron', hour=0, minute=5)  # Run daily at 00:05
    scheduler.add_job(check_subscription_renewals, 'cron', hour=1, minute=0)  # Run daily at 01:00
    
    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started")
