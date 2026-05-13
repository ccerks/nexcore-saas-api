import os
import pika
import json
import requests
from app.core.config import settings

def process_notification(ch, method, properties, body):
    """
    Handles events from the 'nexcore_notifications' queue.
    Responsible for external communications (e.g., Discord).
    """
    data = json.loads(body)
    event_type = data.get("event")
    
    if event_type == "PRODUCT_DELETED":
        message = (
            f"🗑️ **Product Deleted**\n"
            f"**Store ID:** {data.get('tenant_id')}\n"
            f"**Item:** {data.get('product_name')} ({data.get('sku')})\n"
            f"**Actor ID:** {data.get('deleted_by')}"
        )
        
        requests.post(settings.DISCORD_WEBHOOK_URL, json={"content": message})
        print(f" [x] Discord notification sent for {data.get('sku')}")
        
    ch.basic_ack(delivery_tag=method.delivery_tag)

def process_task(ch, method, properties, body):
    """
    Handles events from the 'nexcore_tasks' queue.
    Translates public URLs to physical internal file paths before deletion.
    """
    message = json.loads(body)
    action = message.get("action")
    data = message.get("data", {})

    if action == "delete_image":
        raw_url = data.get("file_path", "")
        
        # Path Translation: Converts public URL to physical container path
        # Example: "/static/products/123.png" -> "/app/uploads/products/123.png"
        physical_path = raw_url.replace("/static/", "/app/uploads/")

        if physical_path and os.path.exists(physical_path):
            try:
                os.remove(physical_path)
                print(f" [x] Orphaned file deleted: {physical_path}")
            except OSError as e:
                print(f" [!] Error deleting file {physical_path}: {e}")
        else:
            print(f" [-] File not found or invalid path: {physical_path}")
            
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker():
    """
    Initializes the RabbitMQ connection and starts consuming from multiple queues.
    """
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    # Fair dispatch: Ensures the worker processes one message at a time
    channel.basic_qos(prefetch_count=1)

    # Setup Notifications Queue Consumer
    channel.queue_declare(queue='nexcore_notifications', durable=True)
    channel.basic_consume(
        queue='nexcore_notifications', 
        on_message_callback=process_notification
    )

    # Setup Tasks Queue Consumer
    channel.queue_declare(queue='nexcore_tasks', durable=True)
    channel.basic_consume(
        queue='nexcore_tasks', 
        on_message_callback=process_task
    )

    print(' [*] Background Worker is active. Listening to multiple queues...')
    channel.start_consuming()

if __name__ == '__main__':
    start_worker()