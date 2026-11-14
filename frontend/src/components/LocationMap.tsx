import { Circle, CircleMarker, MapContainer, Marker, Popup, TileLayer, Tooltip } from "react-leaflet";
import { divIcon } from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Mission, World } from "../lib/types";

function scoreTone(score: number | undefined, active: boolean) {
  if (active) return { color: "#9a6bff", fillColor: "#9a6bff", fillOpacity: 0.32 };
  if (score === undefined) return { color: "#4a86ff", fillColor: "#4a86ff", fillOpacity: 0.14 };
  if (score >= 80) return { color: "#2fe6a8", fillColor: "#2fe6a8", fillOpacity: 0.2 };
  if (score >= 60) return { color: "#ffc04d", fillColor: "#ffc04d", fillOpacity: 0.16 };
  return { color: "#7aa2ff", fillColor: "#7aa2ff", fillOpacity: 0.12 };
}

export default function LocationMap({ world, mission }: { world: World; mission: Mission | null }) {
  const defaultCity = Object.keys(world.cities)[0];
  const focusCity = mission?.recommendation?.city ?? defaultCity;
  const focus = world.cities[focusCity] ?? world.cities[defaultCity];
  const cityEntries = Object.entries(world.cities);
  const liveCoords = `${focus.lat.toFixed(4)}°, ${focus.lon.toFixed(4)}°`;
  const leadCounts = Object.fromEntries(cityEntries.map(([city]) => [city, 0]));
  for (const lead of world.leads) {
    if (lead.city in leadCounts) leadCounts[lead.city] += 1;
  }

  const cityBounds = cityEntries.map(([_, city]) => [city.lat, city.lon] as [number, number]);

  return (
    <div className="location-map-wrap">
      <MapContainer
        center={[focus.lat, focus.lon]}
        bounds={cityBounds}
        scrollWheelZoom={false}
        className="leaflet-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {cityEntries.map(([name, city]) => {
          const score = mission?.recommendation?.scores[name];
          const active = name === focusCity;
          const radius = 8500 + (score ?? 0) * 90 + (leadCounts[name] ?? 0) * 2400;
          const tone = scoreTone(score, active);
          return (
            <Circle
              key={name}
              center={[city.lat, city.lon]}
              radius={radius}
              pathOptions={{ ...tone, weight: active ? 2.6 : 1.2, opacity: active ? 1 : 0.85 }}
            >
              <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                {name} {score !== undefined ? `· ${score}` : ""}
              </Tooltip>
              <Popup>
                <strong>{name}</strong>
                <div>Recommended score: {score ?? "n/a"}</div>
                <div>Market factors: {leadCounts[name]} lead(s) / relevant signals</div>
              </Popup>
            </Circle>
          );
        })}

        {cityEntries.map(([name, city]) => {
          const score = mission?.recommendation?.scores[name];
          const active = name === focusCity;
          const size = active ? 14 : 10;
          const tone = scoreTone(score, active);
          return (
            <CircleMarker
              key={`${name}-pin`}
              center={[city.lat, city.lon]}
              radius={size}
              pathOptions={{ ...tone, weight: active ? 3 : 1.5, opacity: active ? 1 : 0.9 }}
            >
              <Popup>
                <strong>{name}</strong>
                <div>Opportunity score: {score ?? "n/a"}</div>
                <div>Business risk and demand signal zone.</div>
              </Popup>
            </CircleMarker>
          );
        })}

        {cityEntries.map(([name, city]) => {
          const score = mission?.recommendation?.scores[name];
          const active = name === focusCity;
          return (
            <Marker
              key={`${name}-label`}
              position={[city.lat, city.lon]}
              icon={divIcon({
                className: "city-label-wrap",
                html: `<div class="city-label ${active ? "active" : ""}">${name}${score !== undefined ? ` · ${score}` : ""}</div>`,
                iconSize: [0, 0],
                iconAnchor: [0, 0],
              })}
            />
          );
        })}
      </MapContainer>
      <div className="location-focus-card" aria-live="polite">
        <div className="location-focus-name">{focusCity}</div>
        <div className="location-focus-coords">Live location: {liveCoords}</div>
      </div>
      <div className="location-map-legend">
        <span className="location-map-key"><i className="tone purple" />Focused city</span>
        <span className="location-map-key"><i className="tone green" />High fit</span>
        <span className="location-map-key"><i className="tone amber" />Watchlist</span>
        <span className="location-map-key"><i className="tone blue" />Demand / risk ring</span>
      </div>
    </div>
  );
}
