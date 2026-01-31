// -----------------------------------------------------
// MAP INITIALIZATION
// -----------------------------------------------------

const map = L.map("map");
let selectedKhasraLayer = null;

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap contributors"
}).addTo(map);

// -----------------------------------------------------
// NDVI STACK OVERLAY
// -----------------------------------------------------

let ndviOverlay = null;

fetch("https://127.0.0.1:8000/ndvi-bounds")
    .then(res => res.json())
    .then(data => {
        const bounds = data.bounds;

        ndviOverlay = L.imageOverlay(
            "https://127.0.0.1:8000/ndvi-image",
            bounds,
            { opacity: 1.0 }
        ).addTo(map);

        map.fitBounds(bounds);
    });


// -----------------------------------------------------
// NDVI TREND CHART
// -----------------------------------------------------

let ndviChart = null;

function drawNDVIChart(ndvi) {
    const ctx = document.getElementById("ndviChart").getContext("2d");
    if (ndviChart) ndviChart.destroy();

    ndviChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: ["Nov", "Dec", "Jan", "Feb"],
            datasets: [{
                label: "NDVI Trend",
                data: [
                    ndvi.NDVI_Nov,
                    ndvi.NDVI_Dec,
                    ndvi.NDVI_Jan,
                    ndvi.NDVI_Feb
                ],
                borderColor: "green",
                backgroundColor: "rgba(0,128,0,0.25)",
                tension: 0.3,
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: -0.4,
                    max: 1.0,
                    title: { display: true, text: "NDVI" }
                }
            }
        }
    });
}

// -----------------------------------------------------
// CROP COLOR MAP
// -----------------------------------------------------

const cropColors = {
    "कोई फ़सल नहीं": "#bdbdbd",
    "चना": "#4daf4a",
    "गेहूँ": "#ffd92f",
    "सरसों": "#e41a1c",
    "अन्‍य फसल": "#984ea3"
};

// -----------------------------------------------------
// LEGEND
// -----------------------------------------------------

const legend = L.control({ position: "bottomright" });

legend.onAdd = function () {
    const div = L.DomUtil.create("div", "legend");
    div.innerHTML = "<b>Crop Classes</b>";
    for (let crop in cropColors) {
        div.innerHTML += `
            <div>
                <span class="lg" style="background:${cropColors[crop]}"></span>
                ${crop}
            </div>
        `;
    }
    return div;
};
legend.addTo(map);

// -----------------------------------------------------
// KHASRA CADASTRAL + LABEL LAYERS
// -----------------------------------------------------

let cadastralLayer = null;
let khasraLabelLayer = L.layerGroup();   // ❌ NOT added to map
let labelsVisible = false;               // 🔥 OFF by default

// Font size based on zoom (labels appear only when zoomed well)
function getLabelFontSize(zoom) {
    // Completely hide labels at low zoom
    if (zoom < 16) return 0;

    // Smooth linear growth
    const size = 10 + (zoom - 16) * 2;

    // Clamp between 10px and 16px
    return Math.min(16, Math.max(10, size));
}


fetch("https://127.0.0.1:8000/khasra-geojson")
    .then(res => res.json())
    .then(geojson => {

        cadastralLayer = L.geoJSON(geojson, {
            style: {
                color: "#555",
                weight: 1,
                fill: false
            }
        }).addTo(map);

        // ---- CREATE LABELS (NOT SHOWN YET) ----
        geojson.features.forEach(f => {
            const center = L.geoJSON(f.geometry).getBounds().getCenter();

            const label = L.marker(center, {
                interactive: false,
                icon: L.divIcon({
                    className: "khasra-label",
                    html: `<span>${f.properties.khasra_no}</span>`,
                    iconSize: null
                })
            });

            khasraLabelLayer.addLayer(label);
        });
    });

// -----------------------------------------------------
// LABEL VISIBILITY & RESIZE ON ZOOM
// -----------------------------------------------------

function updateLabelVisibility() {
    if (!labelsVisible) return;

    const zoom = map.getZoom();
    const size = getLabelFontSize(zoom);

    khasraLabelLayer.eachLayer(layer => {
        const el = layer.getElement();
        if (!el) return;

        if (size > 0) {
            el.style.display = "block";
            el.style.fontSize = size + "px";
        } else {
            el.style.display = "none";
        }
    });
}

map.on("zoomend", updateLabelVisibility);

// -----------------------------------------------------
// LABEL TOGGLE CONTROL
// -----------------------------------------------------

const labelToggle = L.control({ position: "topright" });

labelToggle.onAdd = function () {
    const btn = L.DomUtil.create("button", "label-toggle");
    btn.innerText = "🏷 Labels OFF";

    btn.onclick = () => {
        labelsVisible = !labelsVisible;

        if (labelsVisible) {
            map.addLayer(khasraLabelLayer);
            updateLabelVisibility();
            btn.innerText = "🏷 Labels ON";
        } else {
            map.removeLayer(khasraLabelLayer);
            btn.innerText = "🏷 Labels OFF";
        }
    };
    return btn;
};

labelToggle.addTo(map);

// -----------------------------------------------------
// CLICK → PREDICTION → COLOR SELECTED KHASRA
// -----------------------------------------------------

map.on("click", async function (e) {

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    L.popup()
        .setLatLng(e.latlng)
        .setContent("⏳ NDVI निकाल रहे हैं और फसल अनुमान किया जा रहा है...")
        .openOn(map);

    try {
        const response = await fetch("https://127.0.0.1:8000/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ latitude: lat, longitude: lon })
        });

        const data = await response.json();

        if (data.outside === true) {
            if (ndviChart) ndviChart.destroy();
            return;
        }

        // const color = cropColors[data.predicted_crop] || "#000";

        if (selectedKhasraLayer) {
            map.removeLayer(selectedKhasraLayer);
        }

        // selectedKhasraLayer = L.geoJSON(data.geometry, {
        //     style: {
        //         color: color,
        //         fillColor: color,
        //         fillOpacity: 1,
        //         weight: 3
        //     }
        // }).addTo(map);
        
        // 🔹 Update left panel crop info
        document.getElementById("predictedCrop").innerText =
        data.predicted_crop || "--";

        document.getElementById("actualCrop").innerText =
        data.actual_crop || "--";

        document.getElementById("cropName").innerText =
        data.crop_name || "--";

        L.popup()
            .setLatLng(e.latlng)
            .setContent(`
                <b>🌾 अनुमानित रबी फसल:</b> ${data.predicted_crop}<br>
                <b>🌾 वास्तविक रबी फसल:</b> ${data.crop_name}<br>
                <b>खसरा नंबर:</b> ${data.khasra_no}<br>
                <b>क्षेत्रफल (ha):</b> ${data.area_ha.toFixed(2)}
            `)
            .openOn(map);

        drawNDVIChart(data.ndvi);

    } catch (err) {
        console.error(err);
    }
});

// -----------------------------------------------------
// KHASRA SEARCH → SAME AS MAP CLICK LOGIC
// -----------------------------------------------------

document.getElementById("khasraSearchBtn").addEventListener("click", async () => {
    const khasraNo = document.getElementById("khasraSearchInput").value.trim();

    if (!khasraNo) {
        alert("कृपया खसरा नंबर दर्ज करें");
        return;
    }

    try {
        const response = await fetch("https://127.0.0.1:8000/predict-by-khasra", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ khasra_no: khasraNo })
        });

        const data = await response.json();
        console.log(data);

        if (data.outside === true) {
            alert("खसरा नहीं मिला");
            return;
        }

        const color = cropColors[data.predicted_crop] || "#000";

        if (selectedKhasraLayer) {
            map.removeLayer(selectedKhasraLayer);
        }

        selectedKhasraLayer = L.geoJSON(data.geometry, {
            style: {
                color: color,
                fillColor: color,
                fillOpacity: 0.5,
                weight: 1
            }
        }).addTo(map);

        // Zoom to khasra
        map.fitBounds(selectedKhasraLayer.getBounds());

        // Update left panel
        document.getElementById("predictedCrop").innerText =
            data.predicted_crop || "--";

        document.getElementById("actualCrop").innerText =
            data.actual_crop || "--";

        document.getElementById("cropName").innerText =
            data.crop_name || "--";

        // Popup
        L.popup()
            .setLatLng(selectedKhasraLayer.getBounds().getCenter())
            .setContent(`
                <b>🌾 अनुमानित रबी फसल:</b> ${data.predicted_crop}<br>
                <b>🌾 वास्तविक रबी फसल:</b> ${data.crop_name}<br>
                <b>खसरा नंबर:</b> ${data.khasra_no}<br>
                <b>क्षेत्रफल (ha):</b> ${data.area_ha.toFixed(2)}
            `)
            .openOn(map);

        drawNDVIChart(data.ndvi);

    } catch (err) {
        console.error(err);
    }
});
