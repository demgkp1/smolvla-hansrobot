class HansProtocolError(Exception):
    """HansRobot protocol parsing error."""


def parse_response(response: str) -> dict:
    """
    Parse a HansRobot protocol response.

    Expected general format:

        Command,Status,Field1,Field2,...,;

    Returns:
        {
            "command": str,
            "status": str,
            "fields": list[str],
            "raw": str,
        }

    Raises:
        HansProtocolError: if the response is empty or malformed.
    """
    response = response.strip()

    if not response:
        raise HansProtocolError("收到空响应")

    if not response.endswith(",;"):
        raise HansProtocolError(
            f"响应缺少协议结束符 ',;': {response!r}"
        )

    # Remove the protocol terminator.
    payload = response[:-2]

    parts = payload.split(",")

    if len(parts) < 2:
        raise HansProtocolError(
            f"无效的协议响应: {response!r}"
        )

    command = parts[0]
    status = parts[1]
    fields = parts[2:]

    if not command:
        raise HansProtocolError("响应缺少命令名称")

    if not status:
        raise HansProtocolError("响应缺少状态字段")

    return {
        "command": command,
        "status": status,
        "fields": fields,
        "raw": response,
    }
