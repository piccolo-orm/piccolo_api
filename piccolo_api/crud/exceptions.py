class MalformedQuery(Exception):
    """
    Raised when the query is malformed - for example, the column names are
    unrecognised. The exception should be handled internally by PiccoloCRUD,
    and shouldn't bleed out to the wider application.
    """

    pass
