// static/script.js

// 1. Die Uhr live updaten (jede Sekunde)
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('de-DE', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}
setInterval(updateClock, 1000);
updateClock(); // Sofort einmal ausführen

// 2. Daten vom Backend laden
async function updateDashboard() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();

        // --- KALENDER UPDATEN ---
        const timeline = document.getElementById('timeline');
        timeline.innerHTML = ''; // Alte Daten löschen
        
        // Falls wir losgehen müssen, bauen wir die rote Warnlinie ein
        if (data.leave_time) {
            timeline.innerHTML += `
                <div class="leave-line">
                    🚶‍♂️ LOSGEHEN UM ${data.leave_time} UHR
                </div>
            `;
        }

        // Termine durchgehen und HTML generieren
        data.events.forEach(event => {
            const shortLocation = event.location.split(',')[0]; 
            timeline.innerHTML += `
                <div class="event-block" style="border-left-color: ${event.color}">
                    <div class="event-time">${event.start_clock} Uhr</div>
                    <div class="event-title">${event.title}</div>
                    <div class="event-location">📍 ${shortLocation}</div>
                </div>
            `;
        });

        // --- MVG ÖPNV UPDATEN ---
        const transitDiv = document.getElementById('transit-info');
        if (data.transit && data.transit.legs) {
            
            const shortTarget = data.transit_target_station.split(',')[0];
            
            let legsHtml = '';
            data.transit.legs.forEach(leg => {
                let delayHtml = leg.delay > 0 
                    ? `<span style="color:#ff4d4d; margin-left: 5px;">+${leg.delay}</span>` 
                    : '';
                
                let typeClass = 'default-line';
                if (leg.name.includes('U')) typeClass = 'u-bahn';
                else if (leg.name.includes('S')) typeClass = 's-bahn';
                else if (leg.name.includes('Bus')) typeClass = 'bus';
                else if (leg.name.includes('Fuß')) typeClass = 'walk';

                legsHtml += `
                    <div class="leg-row">
                        <div class="leg-time">${leg.departure} ${delayHtml}</div>
                        <div class="mvg-line ${typeClass}">${leg.name}</div>
                        <div class="leg-dir">${leg.direction}</div>
                    </div>
                `;
            });

            transitDiv.innerHTML = `
                <div class="transit-card">
                    <div style="color: var(--text-muted); margin-bottom: 15px; font-weight: bold;">
                        Route nach ${shortTarget} (${data.transit.total_duration} Min)
                    </div>
                    <div class="legs-container">
                        ${legsHtml}
                    </div>
                </div>
            `;
        } else {
            transitDiv.innerHTML = `<div class="transit-card" style="color: var(--text-muted);">Aktuell keine Verbindung nötig.</div>`;
        }

    } catch (error) {
        console.error("Fehler beim Laden der API:", error);
    }
}

// Sofort beim Start Daten laden und dann jede Minute aktualisieren
updateDashboard();
setInterval(updateDashboard, 60000);