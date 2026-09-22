from protocol.parser import HansProtocolError
from protocol.parser import parse_response


def test_parse_success():
    response = "ReadRobotState,OK,0,1,0,;"

    result = parse_response(response)

    assert result["command"] == "ReadRobotState"
    assert result["status"] == "OK"
    assert result["fields"] == ["0", "1", "0"]
    assert result["raw"] == response


def test_parse_empty_response():
    try:
        parse_response("")
    except HansProtocolError:
        pass
    else:
        raise AssertionError(
            "Expected HansProtocolError for empty response"
        )


def test_parse_missing_terminator():
    response = "ReadRobotState,OK,0,1,0"

    try:
        parse_response(response)
    except HansProtocolError:
        pass
    else:
        raise AssertionError(
            "Expected HansProtocolError for malformed response"
        )


def test_parse_missing_command():
    response = ",OK,0,1,0,;"

    try:
        parse_response(response)
    except HansProtocolError:
        pass
    else:
        raise AssertionError(
            "Expected HansProtocolError for missing command"
        )


def test_parse_missing_status():
    response = "ReadRobotState,,0,1,0,;"

    try:
        parse_response(response)
    except HansProtocolError:
        pass
    else:
        raise AssertionError(
            "Expected HansProtocolError for missing status"
        )


if __name__ == "__main__":
    test_parse_success()
    test_parse_empty_response()
    test_parse_missing_terminator()
    test_parse_missing_command()
    test_parse_missing_status()

    print("[OK] All protocol parser tests passed.")

