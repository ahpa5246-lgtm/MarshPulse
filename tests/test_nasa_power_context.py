"""NASA POWER temporal rigor; fixture values are synthetic, NOT weather observations."""
import datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from nasa_power_context import parse_daily_power,past_only_features,request_url

class PowerContextTests(unittest.TestCase):
    def test_nasa_daily_url_has_only_approved_parameters_and_dates(self):
        url=request_url(31.6,47.7,dt.date(2025,1,1),dt.date(2025,2,1))
        self.assertIn("PRECTOTCORR%2CT2M",url)
        self.assertIn("community=AG",url)
        self.assertIn("20250101",url)
        self.assertNotIn("KAGGLE",url)
    def test_previous_weather_never_reads_target(self):
        months={
            "2025-11":{"rainfall_mm_month":5,"temperature_c_mean":14},
            "2025-12":{"rainfall_mm_month":10,"temperature_c_mean":18},
            "2026-01":{"rainfall_mm_month":15,"temperature_c_mean":20},
            "2026-02":{"rainfall_mm_month":999,"temperature_c_mean":90}}
        before=past_only_features(months,"2026-02")
        self.assertEqual(before["rainfall_last_3months_mm"],30)
        self.assertEqual(before["source_last_month"],"2026-01")
        months["2026-02"]["rainfall_mm_month"]=20000
        self.assertEqual(before,past_only_features(months,"2026-02"))
    def test_missing_past_month_is_not_zero_rain(self):
        months={"2026-01":{"rainfall_mm_month":0,"temperature_c_mean":19}}
        self.assertIsNone(past_only_features(months,"2026-02"))
    def test_incomplete_or_missing_days_discarded(self):
        daily={"properties":{"parameter":{"PRECTOTCORR":{},"T2M":{}}}}
        for day in range(1,32):
            key=f"202501{day:02d}"
            daily["properties"]["parameter"]["PRECTOTCORR"][key]=1.
            daily["properties"]["parameter"]["T2M"][key]=20.
        daily["properties"]["parameter"]["PRECTOTCORR"]["20250201"]=9.
        daily["properties"]["parameter"]["T2M"]["20250201"]=30.
        result=parse_daily_power(daily)
        self.assertAlmostEqual(result["2025-01"]["rainfall_mm_month"],31)
        self.assertNotIn("2025-02",result)
    def test_missing_or_negative_rain_never_fake_zero(self):
        payload={"properties":{"parameter":{
            "PRECTOTCORR":{"20250101":-999.},
            "T2M":{"20250101":30.}}}}
        self.assertEqual(parse_daily_power(payload),{})

if __name__=="__main__":unittest.main()
