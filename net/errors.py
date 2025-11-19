class PrematureStreamEnd(Exception):
    """
    If the HTTP TCP stream ends before a full header and body is sent
    """
    pass

class InvalidRequestHead(Exception):
    """
    An issue was detected in the HTTP header
    """
    pass

class RequestTooLarge(Exception):
    """
    The request is larger than the maximum allowed size
    """
    pass
