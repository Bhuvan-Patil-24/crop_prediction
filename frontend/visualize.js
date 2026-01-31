// -----------------------------------------------------
// DATE LABEL MAP
// -----------------------------------------------------

const monthDates = {
    "Nov": "14 November 2024",
    "Dec": "16 December 2024",
    "Jan": "25 January 2025",
    "Feb": "23 February 2025",
};

// -----------------------------------------------------
// MAP INITIALIZATION (CRS.Simple)
// -----------------------------------------------------

const rgbMap = L.map("rgbMap", {
    crs: L.CRS.Simple,
    minZoom: -5,
    maxZoom: 5
});

const ndviMap = L.map("ndviMap");

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors"
}).addTo(ndviMap);

let rgbLayer = null;
let ndviLayer = null;
let cadastralLayer = null;

async function loadImages(month) {
    try {
        // Update date label
        document.getElementById("dateLabel").innerText =
            `📅 ${monthDates[month]}`;

        // 🔹 Fetch geographic bounds ONCE (shared by RGB + NDVI)
        const boundsRes = await fetch("https://127.0.0.1:8000/ndvi-bounds");
        const boundsData = await boundsRes.json();
        const bounds = boundsData.bounds;

        // ---------------- RGB (IMAGE ONLY, NO GIS) ----------------
        const rgbRes = await fetch(
            `https://127.0.0.1:8000/viz/rgb-image?month=${month}`
        );
        const rgbBlob = await rgbRes.blob();
        const rgbImg = new Image();
        rgbImg.src = URL.createObjectURL(rgbBlob);

        rgbImg.onload = () => {
            const bounds = [[0, 0], [rgbImg.height, rgbImg.width]];

            if (rgbLayer) rgbMap.removeLayer(rgbLayer);

            rgbLayer = L.imageOverlay(rgbImg.src, bounds).addTo(rgbMap);
            rgbMap.fitBounds(bounds);
        };

        // ---------------- NDVI ----------------
        if (ndviLayer) ndviMap.removeLayer(ndviLayer);

        ndviLayer = L.imageOverlay(
            `https://127.0.0.1:8000/viz/ndvi-image?month=${month}`,
            bounds,
            { opacity: 0.8 }
        ).addTo(ndviMap);

        ndviMap.fitBounds(bounds);


        // ---------------- CADASTRAL (LOAD ONCE) ----------------
        if (!cadastralLayer) {
            const res = await fetch("https://127.0.0.1:8000/khasra-geojson");
            const geojson = await res.json();

            cadastralLayer = L.geoJSON(geojson, {
                style: {
                    color: "#555",
                    weight: 1,
                    fillColor: "#dddddd",
                    fillOpacity: 0
                }
            }).addTo(ndviMap);
        }

    } catch (err) {
        console.error("❌ Raster load error:", err);
        alert("Failed to load raster images.");
    }
}


// -----------------------------------------------------
// NDVI CLICK → VALUE POPUP
// -----------------------------------------------------

ndviMap.on("click", async e => {
    const latlng = e.latlng;

    if (!ndviLayer || !ndviLayer.getBounds().contains(latlng)) {
        L.popup()
            .setLatLng(latlng)
            .setContent("❌ Outside NDVI raster")
            .openOn(ndviMap);
        return;
    }

    const month = document.getElementById("monthSelect").value;

    const payload = {
        latitude: latlng.lat,
        longitude: latlng.lng,
        month: month
    };

    try {
        const res = await fetch("https://127.0.0.1:8000/viz/ndvi-value", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        L.popup()
            .setLatLng(latlng)
            .setContent(
                typeof data.ndvi === "number"
                    ? `<b>📊 NDVI:</b> ${data.ndvi.toFixed(3)}`
                    : `<b>📊 NDVI:</b> No data`
            )
            .openOn(ndviMap);

    } catch (err) {
        console.error("🔥 NDVI fetch failed:", err);
    }
});

// -----------------------------------------------------
// MONTH CHANGE
// -----------------------------------------------------

document.getElementById("monthSelect").addEventListener("change", e => {
    loadImages(e.target.value);
});

// -----------------------------------------------------
// INITIAL LOAD
// -----------------------------------------------------

loadImages("Nov");
