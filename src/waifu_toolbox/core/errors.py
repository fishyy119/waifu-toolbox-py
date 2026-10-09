class OperationError(Exception):
    """业务条件不满足时终止操作，由 CLI 或 API 边界处理。"""
