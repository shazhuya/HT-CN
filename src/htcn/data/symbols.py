from __future__ import annotations

from .models import Board, Exchange


def classify_symbol(symbol: str) -> tuple[Exchange, Board]:
    code = symbol.strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"invalid A-share symbol: {symbol!r}")

    if code.startswith(("600", "601", "603", "605", "688", "689")):
        board = Board.STAR if code.startswith(("688", "689")) else Board.MAIN
        return Exchange.SSE, board
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        board = Board.CHINEXT if code.startswith(("300", "301")) else Board.MAIN
        return Exchange.SZSE, board
    if code.startswith(("4", "8", "9")):
        return Exchange.BSE, Board.BSE

    raise ValueError(f"unsupported A-share symbol prefix: {symbol!r}")


def instrument_id_from_symbol(symbol: str) -> str:
    exchange, _ = classify_symbol(symbol)
    return f"{exchange.value}.{symbol}"


def symbol_from_instrument_id(instrument_id: str) -> str:
    try:
        exchange, symbol = instrument_id.split(".", 1)
    except ValueError as exc:
        raise ValueError(f"invalid instrument_id: {instrument_id!r}") from exc
    expected_exchange, _ = classify_symbol(symbol)
    if exchange != expected_exchange.value:
        raise ValueError(
            f"instrument exchange mismatch: {instrument_id!r}; expected {expected_exchange.value}"
        )
    return symbol
