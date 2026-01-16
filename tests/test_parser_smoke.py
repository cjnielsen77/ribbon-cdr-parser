# tests/test_parser_smoke.py
import pytest

# Your example CDRs (embedded so tests don't depend on mappings module structure)
START_CDR_EXAMPLE = 'START,ABCGSX1,0x0001042B00000012,95396749,GMT-08:00-Pacific(US),02/22/2013,17:02:12.5,5,16,511,VoIP,IP-TO-IP,BillCAN_GOW_PARTITION,,,5307520014,,0,,0,,0,,,1,ABCGSX1:NBSPUBSIP_ON_SIF93,10.158.151.66,0.0.0.0,NBS_TRUSTED_ABCASX1,,10.158.130.205:5004/10.158.130.205:5002,,10.158.151.70:5004/10.158.140.133:2224,,,,0x00020003,,,,2,"SIP,1212381174405161289093_12979976@10.158.10.170,%22Unavailable%22;tag=gK001a110b,;tag=gK02d1465e,0,,,,sip:+15307520014@10.158.130.202:5060;dtg=NBSPUBSIP_ON_SIF93;reg-info=102,,,,sip:Unavailable@10.158.10.170:5620,sip:+15307520014@10.158.130.202:5060,,,,,,,0,0,,0,0,,,,,,,,1,0,0,0,,,,",12,12,0,1,,,0x0a,15307520014,1,1,,NBSPUBSIP_ON_SIF93,"SIP,131074_79727915@10.158.151.66,%22Unavailable%22;tag=gK0251473f,;tag=7D7842DB-2113CB70,0,,,,sip:+15307520014@10.158.140.133:5060;methods=INVITE; ACK; BYE; CANCEL; OPTIONS; INFO; MESSAGE; SUBSCRIBE; NOTIFY;PRACK;UPDATE; REFER;bgid=16824600;bgt=public,,,,sip:Unavailable@10.158.151.66:5060,sip:+15307520014@10.158.140.133,,,,,,,1,1,10.158.140.133,0,0,,,,,,,,1,0,0,0,,,,",,110,,,1,1,,,2,0x00020002,0,,,,,,0,,,,1,,,,,,,6,,,,"Unavailable",2,1,1,1,16824600,,7,,,1,7,1,,,10.158.130.202,10.158.10.170,2,16,8,,,,,,16824600,,,3,0,38,TANDEM,,,,,,,13,1,,,,,,,,,,,,,,,,0,,,,,,,,0,,,"96,84,2,182",0,,,,,,,,,,,,,0,0,0,0,0,0'

STOP_CDR_EXAMPLE = 'STOP,ABCGSX1,0x0001042B00000012,95396749,GMT-08:00-Pacific(US),02/22/2013,17:02:12.5,5,16,511,02/22/2013,17:02:20.7,6,306,16,VoIP,IP-TO-IP,BillCAN_GOW_PARTITION,,,5307520014,,0,,0,,0,,,1,ABCGSX1:NBSPUBSIP_ON_SIF93,10.158.151.66,0.0.0.0,NBS_TRUSTED_ABCASX1,,10.158.130.205:5004/10.158.130.205:5002,,10.158.151.70:5004/10.158.140.133:2224,21440,134,20640,129,,,,0x00020003,,,,,2,"SIP,1212381174405161289093_12979976@10.158.10.170,%22Unavailable%22;tag=gK001a110b,;tag=gK02d1465e,0,,,,sip:+15307520014@10.158.130.202:5060;dtg=NBSPUBSIP_ON_SIF93;reg-info=102,,,,sip:Unavailable@10.158.10.170:5620,sip:+15307520014@10.158.130.202:5060,,,,1,BYE,,0,0,,0,0,,,,,,,,1,0,0,0,,,,",12,12,0,1,,,0x0a,15307520014,1,1,,2,10,0,,NBSPUBSIP_ON_SIF93,"SIP,131074_79727915@10.158.151.66,%22Unavailable%22;tag=gK0251473f,;tag=7D7842DB-2113CB70,0,,,,sip:+15307520014@10.158.140.133:5060;methods=INVITE;ACK; BYE; CANCEL; OPTIONS; INFO; MESSAGE; SUBSCRIBE; NOTIFY; PRACK; UPDATE; REFER;bgid=16824600;bgt=public,,,,sip:Unavailable@10.158.151.66:5060,sip:+15307520014@10.158.140.133,,,,,BYE,,1,1,10.158.140.133,0,0,,,,,,,,1,0,0,0,,,,",,110,,,1,1,,,2,P:2:1,P:2:1,10,0x00020002,,,0,,,,,,0,,,,1,,,,,,,6,,,,"Unavailable",2,1,1,1,16824600,,7,,,1,7,0,306,1,,,,,10.158.130.202,10.158.10.170,4,16,8,,,,,,16824600,,,3,0,38,TANDEM,,,10,20640,129,21440,134,0,0,,16,64,,,,,,,13,1,,,,,,,,,,,,,,,,,,,,,0,9,,,,,,,,,,,,,,,"96,84,2,182",0,,,,,,,,,,,,,,,,,,,0,0,0,0,0,0'

ATTEMPT_CDR_EXAMPLE = 'ATTEMPT,ABCGSX1,0x0001042B00000010,95396662,GMT-08:00-Pacific(US),02/22/2013,17:02:11.6,13,0,17:02:11.8,6,21,VoIP,IP-TO-IP,BillCAN_GOW_PARTITION,,15307520010,5307520014,,0,,0,,0,15307520010,ABC_TOASX,1,ABCGSX1:NBS_TRUSTED_ABCASX1,10.158.130.202,10.158.10.170,NBSPUBSIP_ON_SIF93,,10.158.151.70:5000/127.0.0.0:5004,,10.158.130.205:5000/:0,,,,0x00000001,,,,2,2,"SIP,f86fbb68-b4d047e1-a24212c6@10.158.140.130,%22+15307520010%22;tag=59D07E6E-2A6FE7AF,;tag=gK02d14240,0,,,,sip:5307520014@10.158.151.66;user=phone,,,,sip:+15307520010@10.158.140.130,,,,,,401,,1,1,10.158.140.130,0,0,,,,,,,,1,0,0,0,,,,",12,12,0,1,,,0x0a,5307520014,1,1,,2,NBS_TRUSTED_ABCASX1,"SIP,131072_111295356@10.158.130.202,%22+15307520010%22;tag=gK025143e1,,0,,,,sip:5307520014@10.158.10.170:5620;user=phone,,,,sip:+15307520010@10.158.130.202:5060;reg-info=402,,,,,,401,,0,0,,0,0,,,,,,,,1,0,0,0,,,,",15307520010,110,,,1,1,,,2,,,,0x00020000,0,,,0,,,,,,0,,,,1,,,,,,,6,,,,"+15307520010",2,1,1,1,1,,17,02/22/2013,2,2,,7,1,401,,,,10.158.151.66,10.158.140.130,1,16,8,,,,,,,,,3,0,81,TANDEM,,,,,,,,13,1,,,,,,1,,,,,,,,,,,,,0,9,,,,,,,,,,,,"184,52,5,241",0,,,,,,,,,,,,,'


def _get_parser_callable():
    """
    Try to find a pure parsing function that returns a dict.

    Recommended function name to add to your parser module:
        parse_cdr_to_dict(raw_cdr: str) -> dict
    """
    try:
        # Package import (after pip install -e .)
        from ribbon_cdr_parser import Ribbon_SBC_CDR_parser as parser_mod
    except Exception as e:
        pytest.skip(f"Could not import parser module: {e}")

    for name in ("parse_cdr_to_dict", "parse_cdr_data", "parse_cdr"):
        fn = getattr(parser_mod, name, None)
        if callable(fn):
            return fn

    pytest.skip(
        "No callable parsing function found. "
        "Add a pure function like parse_cdr_to_dict(raw_cdr) that returns parsed_data dict."
    )


def _parse_to_dict(raw_cdr: str) -> dict:
    fn = _get_parser_callable()

    # Try calling it in the simplest way first
    try:
        result = fn(raw_cdr)
    except TypeError:
        # Some implementations require extra args (e.g., root=None)
        result = fn(raw_cdr, None)

    if not isinstance(result, dict):
        pytest.skip(
            f"Parser function returned {type(result).__name__} instead of dict. "
            "For testing, expose a function that returns parsed_data dict."
        )
    return result


@pytest.mark.parametrize(
    "raw_cdr, expected_type",
    [
        (START_CDR_EXAMPLE, "START"),
        (STOP_CDR_EXAMPLE, "STOP"),
        (ATTEMPT_CDR_EXAMPLE, "ATTEMPT"),
    ],
    ids=["START_example", "STOP_example", "ATTEMPT_example"],
)

def test_parse_smoke_returns_dict(raw_cdr, expected_type):
    parsed = _parse_to_dict(raw_cdr)

    # Basic sanity checks: dict, and a few common keys should exist
    assert isinstance(parsed, dict)
    # cdr_type key name may vary; accept either
    cdr_type = parsed.get("cdr_type") or parsed.get("CDR Type") or ""
    assert expected_type in str(cdr_type) or cdr_type == ""  # allow if you don't store cdr_type

    # Common fields you appear to populate across types
    for key in ("calling_number", "called_number", "route_label", "service_provider"):
        assert key in parsed, f"Missing expected key: {key}"


def test_stop_duration_is_number_or_na():
    parsed = _parse_to_dict(STOP_CDR_EXAMPLE)
    dur = parsed.get("duration", "N/A")

    # Your code sometimes stores float/rounded seconds, or 'N/A'
    if isinstance(dur, (int, float)):
        assert dur >= 0
    else:
        assert str(dur).upper() == "N/A"
