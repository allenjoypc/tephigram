from flask import Flask, request, jsonify, send_from_directory
from decoder import decode_ttaa
import matplotlib.pyplot as plt
import numpy as np
import metpy.calc as mpcalc
from metpy.plots import SkewT, Hodograph
from metpy.units import units
import os
import uuid

app = Flask(__name__)

# ---------------- SERVE IMAGE ----------------
@app.route('/outputs/<filename>')
def get_image(filename):
    return send_from_directory('outputs', filename)

# ---------------- MAIN API ----------------
@app.route('/plot', methods=['POST'])
def plot():
    try:
        data = request.get_json(force=True)
        if not data or "data" not in data:
            return jsonify({"error": "No TTAA data provided"}), 400

        raw_data = data["data"]

        # ---------------- DECODE TTAA ----------------
        p, T, Td, wind_dir, wind_speed, height = decode_ttaa(raw_data)

        # Assign units
        p = p * units.hPa
        z = height * units.m
        T = T * units.degC
        Td = Td * units.degC
        wind_speed = wind_speed * units.knots
        wind_dir = wind_dir * units.degrees

        # Convert to u,v wind components
        u, v = mpcalc.wind_components(wind_speed, wind_dir)

        # ---------------- CREATE OUTPUT FOLDER ----------------
        os.makedirs("outputs", exist_ok=True)
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join("outputs", filename)

        # ---------------- PLOT TEHPHRIGRAM ----------------
        fig = plt.figure(figsize=(14, 10))
        skew = SkewT(fig, rotation=45, rect=(0.05, 0.05, 0.55, 0.90))

        # Shading 0°C Isotherm
        skew.ax.axvspan(0, 0.5, color='lightblue', alpha=0.1)

        # Plot temperature, dewpoint, and wind barbs
        skew.plot(p, T, 'r', lw=2, label='Temperature')
        skew.plot(p, Td, 'g', lw=2, label='Dewpoint')
        skew.plot_barbs(p, u, v)

        skew.ax.set_ylim(1000, 100)
        skew.ax.set_xlim(-20, 30)
        skew.plot_dry_adiabats(lw=1.5, color='orange', alpha=0.6)
        skew.plot_moist_adiabats(lw=1.5, color='green', alpha=0.5)
        skew.plot_mixing_lines(lw=1, alpha=0.3)

        # Surface-Based CAPE/CIN
        sbcape, sbcin = mpcalc.surface_based_cape_cin(p, T, Td)
        prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
        skew.plot(p, prof, 'k', lw=2, label='Parcel Profile')
        skew.shade_cape(p, T, prof, alpha=0.2)
        skew.shade_cin(p, T, prof, Td, alpha=0.2)

        # LCL
        lcl_pressure, lcl_temperature = mpcalc.lcl(p[0], T[0], Td[0])
        skew.plot(lcl_pressure, lcl_temperature, 'ko', markerfacecolor='black', label='LCL')

        # TT-Index and K-Index
        k_index = mpcalc.k_index(p, T, Td)
        total_totals = mpcalc.total_totals_index(p, T, Td)

        # Color-coded Hodograph
        hodo_ax = plt.axes((0.6, 0.55, 0.35, 0.35))
        h = Hodograph(hodo_ax, component_range=80.)
        h.plot_colormapped(u, v, c=z, linewidth=4, label='Wind Height')
        h.add_grid(increment=20, ls='-', lw=1.5, alpha=0.5)
        h.add_grid(increment=10, ls='--', lw=1, alpha=0.3)
        h.ax.set_xticklabels([])
        h.ax.set_yticklabels([])
        h.ax.set_xticks([])
        h.ax.set_yticks([])
        
        # ====== Add Text Annotations for CAPE, CIN, TT & KI ======
        plt.figtext(0.58, 0.37, 'SBCAPE: ', weight='bold', fontsize=12)
        plt.figtext(0.70, 0.37, f'{sbcape:.0f~P}', weight='bold', fontsize=12, color='orangered')
        plt.figtext(0.58, 0.34, 'SBCIN: ', weight='bold', fontsize=12)
        plt.figtext(0.70, 0.34, f'{sbcin:.0f~P}', weight='bold', fontsize=12, color='lightblue')
        plt.figtext(0.58, 0.31, 'K-INDEX: ', weight='bold', fontsize=12)
        plt.figtext(0.70, 0.31, f'{k_index:.0f~P}', weight='bold', fontsize=12, color='blue')
        plt.figtext(0.58, 0.28, 'TT-INDEX: ', weight='bold', fontsize=12)
        plt.figtext(0.70, 0.28, f'{total_totals:.0f~P}', weight='bold', fontsize=12, color='orangered')
       
        # Legends and title
        skew.ax.legend(loc='upper left')
        h.ax.legend(loc='upper left')
        plt.figtext(0.5, 0.95, 'Advanced Skew-T & Hodograph | TTAA Profile',
                    weight='bold', fontsize=16, ha='center')

        # Save plot
        plt.savefig(filepath)
        plt.close(fig)

        # ---------------- RESPONSE ----------------
        return jsonify({
            "message": "Plot created successfully",
            "file_url": f"{request.url_root}outputs/{filename}",
            "SBCAPE": float(sbcape.magnitude),
            "SBCIN": float(sbcin.magnitude),
            "K_INDEX": float(k_index.magnitude),
            "TT_INDEX": float(total_totals.magnitude)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)