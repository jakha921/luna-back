from fastapi import HTTPException, status


class BaseException(HTTPException):  # <-- наследуемся от HTTPException, который наследован от Exception
    """
    change response of exception to
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "message": detail,
            "data": str(e) if str(e) else None
        })
    """
    status_code = 500  # <-- задаем значения по умолчанию
    detail = ""

    def __init__(self, detail: str = None):
        if detail is not None:
            self.detail = detail
        super().__init__(status_code=self.status_code, detail=self.detail)

class ObjectNotFoundException(BaseException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Object not found"

    def __init__(self, detail: str = None):
        super().__init__(detail=detail)


class DuplicateObjectException(BaseException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Duplicate object"

    def __init__(self, detail: str = None):
        super().__init__(detail=detail)


class DatabaseException(BaseException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Database error"

    def __init__(self, detail: str = None):
        super().__init__(detail=detail)


class CustomException(BaseException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Custom exception"

    def __init__(self, detail: str = None):
        super().__init__(detail=detail)
