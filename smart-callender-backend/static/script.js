async function updateDashboard() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();

        // 1. ÖPNV Infos aktualisieren
        if (data.transit) {
            document.getElementById('transit-info').innerHTML = `
                Nächste Fahrt: ${data.transit.line} 
                (in ${data.transit.delay} Min Verspätung)
            `;
        }

        // 2. Kalender-Blöcke rendern
        const timeline = document.getElementById('timeline');
        timeline.innerHTML = ''; // Vorherige löschen
        
        data.events.forEach(event => {
            // Aus der Startzeit (z.B. 10:15) eine Y-Position (Top) berechnen.
            // Beispiel: 1 Minute = 2 Pixel
            const block = document.createElement('div');
            block.className = 'event-block';
            block.style.backgroundColor = event.color;
            // block.style.top = berechnete_pixel + 'px';
            block.innerHTML = `<strong>${event.title}</strong><br>${event.location}`;
            timeline.appendChild(block);
        });

    } catch (error) {
        console.error("Fehler beim Laden der API:", error);
    }
}

// Sofort einmal aufrufen, dann alle 60 Sekunden (60000 ms)
updateDashboard();
setInterval(updateDashboard, 60000);