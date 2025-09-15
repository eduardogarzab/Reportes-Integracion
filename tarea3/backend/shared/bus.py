import os, json
try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
except Exception:
    ServiceBusClient = None
    ServiceBusMessage = None

SB_CONN = os.getenv("SERVICEBUS_CONNECTION_STR")
SB_QUEUE = os.getenv("SERVICEBUS_QUEUE", "transfers")
DEMO_NO_SB = os.getenv("DEMO_NO_SB", "1") == "1"  # demo por defecto

def send_transfer(msg_body: dict, idem_key: str):
    if DEMO_NO_SB or not SB_CONN or ServiceBusClient is None:
        print(f"[DEMO] Transfer encolada virtualmente id={idem_key} body={json.dumps(msg_body)}")
        return
    with ServiceBusClient.from_connection_string(SB_CONN) as client:
        sender = client.get_queue_sender(queue_name=SB_QUEUE)
        with sender:
            msg = ServiceBusMessage(json.dumps(msg_body), message_id=idem_key)
            sender.send_messages(msg)
