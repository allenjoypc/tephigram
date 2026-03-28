import re
import numpy as np

def decode_ttaa(raw_data):
    raw_data = raw_data.upper().replace("\n", " ").replace("=", " ")
    match = re.search(r'TTAA(.*?)(TTBB|TTCC|TTDD|$)', raw_data)
    if not match:
        return [], [], [], [], [], []

    data = match.group(1).replace("/", " ")
    groups = re.findall(r'\b\d{5}\b', data)

    pressure, temperature, dewpoint, wind_dir, wind_speed, height = [], [], [], [], [], []

    i = 2  # Skip date/time + station
    while i + 2 < len(groups):
        try:
            g1, g2, g3 = groups[i], groups[i+1], groups[i+2]

            # Skip missing data
            if g1.startswith("00") or g1.strip("0") == "":
                i += 3
                continue

            # ----- Pressure -----
            if g1.startswith("99"):  # surface
                ppp = int(g1[2:])
                p = 1000 + ppp if ppp < 500 else ppp
            elif g1.startswith("92"): p = 925
            elif g1.startswith("85"): p = 850
            elif g1.startswith("70"): p = 700
            elif g1.startswith("50"): p = 500
            elif g1.startswith("40"): p = 400
            elif g1.startswith("30"): p = 300
            elif g1.startswith("25"): p = 250
            elif g1.startswith("20"): p = 200
            elif g1.startswith("15"): p = 150
            elif g1.startswith("10"): p = 100
            else: 
                i += 3
                continue

            # ----- Temperature -----
            ttt, dd = int(g2[:3]), int(g2[3:]) / 10.0
            temp = ttt / 10.0
            if ttt % 2 == 1:
                temp = -temp
            dew = temp - dd

            # ----- Wind -----
            w_dir = int(g3[:3]) % 360
            w_spd = int(g3[3:]) % 100

            # ----- Height -----
            last3 = int(g1[2:])
            if p == 925:
                h = last3
            elif p == 850:
                h = 1000 + last3
            elif p == 700:
                h = 3000 + last3
            elif p == 500:
                h = 5000 + last3
            elif p == 400:
                h = int(f"{last3}0")   # suffix 0
            elif p == 300:
                h = int(f"{last3}0")   # suffix 0
            elif p in [250, 200, 150, 100]:
                h = int(f"1{last3}0")  # prefix 1 + suffix 0
            else:
                h = np.nan

            # Store
            pressure.append(p)
            temperature.append(temp)
            dewpoint.append(dew)
            wind_dir.append(w_dir)
            wind_speed.append(w_spd)
            height.append(h)

            i += 3

        except:
            i += 3
            continue

    return (np.array(pressure),
            np.array(temperature),
            np.array(dewpoint),
            np.array(wind_dir),
            np.array(wind_speed),
            np.array(height))


# ===== Usage Example =====
if __name__ == "__main__":
    ttaa_sample = """
    TTAA 78001 42220 99991 19613 36010 00/// ///// ///// 92745 17858
    01512 85465 14257 09502 70072 03424 23522 50572 12750 24529
    40739 23121 23535 30943 38157 26056 25066 48156 26072 20209
    60758 25587 15385 65761 26080 10632 67378 26555 88165 66359
    26088 77133 23590 41714 31313 53808 82310=
    """

    p, T, Td, w_dir, w_spd, h = decode_ttaa(ttaa_sample)

    print("Lvl | Press(hPa) | Height(m) | Temp(°C) | DewPt(°C) | WindDir | WindSpd ")
    print("-"*95)
    for i in range(len(p)):
        print(f"{i+1:3d} | {p[i]:10.1f} | {h[i]:9.0f} | {T[i]:7.1f} | "
              f"{Td[i]:9.1f} | {w_dir[i]:7.0f} | {w_spd[i]:7.1f} | ")