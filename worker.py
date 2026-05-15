import os
import time
import json
import requests
import pika
from pika.exceptions import AMQPConnectionError
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from app.core.config import settings

def process_notification(ch: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
    """
    Handles events from the 'nexcore_notifications' queue.
    Responsible for external communications (e.g., Discord) with failure resilience.
    """
    try:
        data = json.loads(body)
        if data.get("event") == "PRODUCT_DELETED":
            message = (
                f"🗑️ **Product Deleted**\n"
                f"**Store ID:** {data.get('tenant_id')}\n"
                f"**Item:** {data.get('product_name')} ({data.get('sku')})\n"
                f"**Actor ID:** {data.get('deleted_by')}"
            )
            response = requests.post(settings.DISCORD_WEBHOOK_URL, json={"content": message}, timeout=5)
            response.raise_for_status()
            print(f" [x] Discord notification sent for {data.get('sku')}")
            
    except requests.RequestException as e:
        print(f" [!] Failed to reach Discord API: {e}")
    except json.JSONDecodeError:
        print(" [!] Failed to decode notification message payload.")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def process_task(ch: BlockingChannel, method: Basic.Deliver, properties: BasicProperties, body: bytes) -> None:
    """
    Handles events from the 'nexcore_tasks' queue.
    Translates public URLs to physical internal file paths before deletion.
    Supports dynamic tenant directories.
    """
    try:
        message = json.loads(body)
        if message.get("action") == "delete_image":
            raw_url = message.get("data", {}).get("file_path", "")
            # Architectural Note: Safely translates the URL preserving the dynamic tenant structure
            physical_path = raw_url.replace("/static/", "/app/uploads/")

            if physical_path and os.path.exists(physical_path):
                os.remove(physical_path)
                print(f" [x] Orphaned file deleted: {physical_path}")
            else:
                print(f" [-] File not found or invalid path: {physical_path}")
                
    except OSError as e:
        print(f" [!] OS Error deleting file: {e}")
    except json.JSONDecodeError:
        print(" [!] Failed to decode task message payload.")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker() -> None:
    """
    Initializes the RabbitMQ connection with a robust backoff mechanism.
    Starts consuming from multiple queues concurrently.
    """
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()
            channel.basic_qos(prefetch_count=1)

            channel.queue_declare(queue='nexcore_notifications', durable=True)
            channel.basic_consume(queue='nexcore_notifications', on_message_callback=process_notification)

            channel.queue_declare(queue='nexcore_tasks', durable=True)
            channel.basic_consume(queue='nexcore_tasks', on_message_callback=process_task)

            print(' [*] Background Worker is active. Listening to multiple queues...')
            channel.start_consuming()
            
        except AMQPConnectionError:
            print(" [!] RabbitMQ is currently unreachable. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f" [!] Fatal worker error: {e}. Restarting loop...")
            time.sleep(5)

if __name__ == '__main__':
    start_worker()