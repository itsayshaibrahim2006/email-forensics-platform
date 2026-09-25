import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import L from "leaflet";
import api from "../api.js";

// Default Leaflet marker icons don't load correctly under bundlers unless re-pointed to CDN assets.
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export default function GeoMap() {
  const { emailId } = useParams();
  const [hops, setHops] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getHops(emailId).then(setHops).catch((e) => setError(e.message));
  }, [emailId]);

  if (error) return <div className="error-state">{error}</div>;
  if (!hops) return <div className="empty-state">Loading routing hops…</div>;

  const located = hops.filter((h) => h.latitude && h.longitude);
  const center = located.length > 0 ? [located[0].latitude, located[0].longitude] : [20, 0];
  const path = located.map((h) => [h.latitude, h.longitude]);

  return (
    <div>
      <Link to={-1} style={{ color: "var(--text-dim)", fontSize: 13 }}>← Back</Link>
      <h1 style={{ marginTop: 10 }}>Routing Hop Map</h1>
      <p className="subtitle">
        Each hop is a mail server the message passed through, origin to destination.
        Hops in red have a chronology or authenticity anomaly.
      </p>

      {located.length === 0 ? (
        <div className="empty-state">
          No geolocatable hops found for this email (private/internal IPs only, or no
          Received: headers present).
        </div>
      ) : (
        <div className="map-wrap">
          <MapContainer center={center} zoom={2} style={{ height: "100%", width: "100%" }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />
            {path.length > 1 && <Polyline positions={path} color="#22d3ee" weight={2} dashArray="6 6" />}
            {located.map((h) => (
              <Marker key={h.hop_index} position={[h.latitude, h.longitude]} icon={defaultIcon}>
                <Popup>
                  <strong>Hop {h.hop_index}</strong><br />
                  IP: {h.ip_address}<br />
                  {h.city ? `${h.city}, ` : ""}{h.country}<br />
                  ISP: {h.isp || "unknown"}
                  {h.is_anomalous && <><br /><strong style={{ color: "#ef4444" }}>⚠ {h.anomaly_reason}</strong></>}
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      )}

      <div className="hop-list">
        {hops.map((h) => (
          <div key={h.hop_index} className={`hop-item ${h.is_anomalous ? "anomalous" : ""}`}>
            <span>#{h.hop_index} {h.ip_address || "unknown ip"} — {h.hostname || "unknown host"}</span>
            <span>{h.city ? `${h.city}, ` : ""}{h.country || "?"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
