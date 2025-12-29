const map = L.map('map').setView([37.5665, 126.9780], 12);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const markerLayer = L.layerGroup().addTo(map);
let heatLayer = null;

const statusEl = document.getElementById('status');
const toggleHeat = document.getElementById('toggleHeat');

const fromEl = document.getElementById('fromId');
const toEl = document.getElementById('toId');
const routeBox = document.getElementById('routeBox');
const resetBtn = document.getElementById('resetSel');

let stationsById = new Map();
let selectedFrom = null;
let selectedTo = null;

function clamp(v, lo, hi){ return Math.max(lo, Math.min(hi, v)); }

function colorFor(st){
  const s = st.shortage_score ?? 0;
  const c = st.congestion_score ?? 0;
  if (s > c && s > 0.15) return '#2b6cb0';  // shortage: blue
  if (c > s && c > 0.15) return '#c53030';  // congestion: red
  return '#2f855a';                          // normal: green
}

function radiusFor(st){
  const s = st.shortage_score ?? 0;
  const c = st.congestion_score ?? 0;
  const severity = Math.max(s, c);
  return clamp(6 + severity * 14, 6, 20);
}

function popupHtml(st){
  const docks = (st.capacity ?? 0) - (st.bikes ?? 0);
  return `
    <div style="min-width:220px">
      <div style="font-weight:800;margin-bottom:6px">${st.name} (${st.station_id})</div>
      <div>자전거: <b>${st.bikes}</b> / 거치대: <b>${st.capacity}</b></div>
      <div>남은 거치대: <b>${docks}</b></div>
      <hr style="border:none;border-top:1px solid #eee;margin:8px 0"/>
      <div>부족 점수: <b>${(st.shortage_score ?? 0).toFixed(3)}</b></div>
      <div>혼잡 점수: <b>${(st.congestion_score ?? 0).toFixed(3)}</b></div>
      <hr style="border:none;border-top:1px solid #eee;margin:8px 0"/>
      <div>인센티브(반납): <b>${st.reward_return}</b>분</div>
      <div>인센티브(대여): <b>${st.reward_rent}</b>분</div>
      <div style="margin-top:6px;color:#666;font-size:12px">updated: ${st.updated_at}</div>
      <div style="margin-top:8px;color:#111;font-size:12px">
        <b>팁:</b> 대여소 두 개를 클릭하면 “과잉→부족 이동” 인센티브를 계산합니다.
      </div>
    </div>
  `;
}

function setRouteBox(text){
  routeBox.textContent = text;
}

async function fetchStations(){
  const res = await fetch('/api/public/stations');
  if (!res.ok) throw new Error('stations fetch failed');
  return await res.json();
}

function clearSelection(){
  selectedFrom = null;
  selectedTo = null;
  fromEl.textContent = '-';
  toEl.textContent = '-';
  setRouteBox('선택된 이동이 없습니다.');
}

resetBtn.addEventListener('click', clearSelection);

async function fetchRouteIncentive(fromId, toId){
  const q = new URLSearchParams({from_station_id: fromId, to_station_id: toId});
  const res = await fetch(`/api/public/route?${q.toString()}`); // ✅ 여기 route로
  if (!res.ok) throw new Error('route incentive fetch failed');
  return await res.json();
}

async function handleStationClick(st){
  if (!selectedFrom){
    selectedFrom = st.station_id;
    fromEl.textContent = selectedFrom;
    setRouteBox('TO 대여소를 선택하세요.');
    return;
  }
  if (!selectedTo){
    selectedTo = st.station_id;
    toEl.textContent = selectedTo;

    try{
      const r = await fetchRouteIncentive(selectedFrom, selectedTo);
      setRouteBox(`거리 ${r.distance_km.toFixed(2)}km / 무료 ${r.free_minutes}분`);
    }catch(e){
      setRouteBox('이동 인센티브 조회 실패');
    }
    return;
  }

  // if already both selected, restart selection with new FROM
  selectedFrom = st.station_id;
  selectedTo = null;
  fromEl.textContent = selectedFrom;
  toEl.textContent = '-';
  setRouteBox('TO 대여소를 선택하세요.');
}

function renderStations(stations){
  markerLayer.clearLayers();
  stationsById.clear();

  const heatPoints = [];

  for (const st of stations){
    stationsById.set(st.station_id, st);

    const marker = L.circleMarker([st.lat, st.lon], {
      radius: radiusFor(st),
      color: colorFor(st),
      weight: 2,
      fillOpacity: 0.8
    });

    marker.bindPopup(popupHtml(st));
    marker.on('click', () => handleStationClick(st));

    marker.addTo(markerLayer);

    // heat: use "need" severity (max of shortage/congestion)
    const sev = Math.max(st.shortage_score ?? 0, st.congestion_score ?? 0);
    heatPoints.push([st.lat, st.lon, sev]);
  }

  if (heatLayer){
    heatLayer.setLatLngs(heatPoints);
  } else {
    heatLayer = L.heatLayer(heatPoints, {radius: 25, blur: 15, maxZoom: 16});
  }
}

toggleHeat.addEventListener('change', () => {
  if (!heatLayer) return;
  if (toggleHeat.checked) heatLayer.addTo(map);
  else map.removeLayer(heatLayer);
});

async function refresh(){
  try{
    statusEl.textContent = '업데이트 중...';
    const stations = await fetchStations();
    renderStations(stations);
    statusEl.textContent = `대여소 ${stations.length}개 표시 중`;
  }catch(e){
    statusEl.textContent = '데이터 로드 실패';
  }
}

clearSelection();
refresh();

// 15초마다 갱신 (원하면 5~30초로 조절)
setInterval(refresh, 15000);