"""Compact GPS processing. Never count unobserved moving gaps as driving."""
import math
from datetime import datetime, timezone

STOP_SPEED = 3 / 1.852  # Traccar knots
STOP_RADIUS_M = 100
MIN_STOP_SECONDS = 180
MAX_MOVING_GAP = 300
MAX_PARKED_GAP = 3 * 3600


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[1], a[2], b[1], b[2]))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 12742000 * math.asin(min(1, math.sqrt(h)))


def compact(rows):
    """timestamp, latitude, longitude, speed(knots), totalDistance(m)."""
    points = {}
    for row in rows:
        try:
            if row.get("valid") is not True:
                continue
            lat, lon = float(row["latitude"]), float(row["longitude"])
            when = datetime.fromisoformat(row["fixTime"].replace("Z", "+00:00"))
            if when.tzinfo is None or not math.isfinite(lat+lon) or abs(lat)>85 or abs(lon)>180:
                continue
            speed = row.get("speed")
            speed = float(speed) if type(speed) in (int,float) and math.isfinite(speed) and speed >= 0 else None
            total = row.get("attributes", {}).get("totalDistance")
            total = float(total) if type(total) in (int,float) and math.isfinite(total) and total>=0 else None
            stamp=when.timestamp()
            points[stamp] = (stamp,lat,lon,speed,total)
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
            continue
    return sorted(points.values())


def analyze(points):
    """Classify consecutive samples, then trim home/destination parking.

    Stationary observations at both ends of a long gap at the same location
    support a *GPS-derived* pause estimate, not certainty of continuous tracking.
    Any other gap >5 min remains unknown and is excluded from drive duration.
    """
    points = sorted({p[0]:p for p in points}.values())
    edges=[]
    for a,b in zip(points,points[1:]):
        seconds=b[0]-a[0]
        meters=distance(a,b)
        if seconds<=0:
            continue
        stopped = a[3] is not None and b[3] is not None and a[3]<STOP_SPEED and b[3]<STOP_SPEED and meters<=STOP_RADIUS_M
        moving = (a[3] is not None and a[3]>=STOP_SPEED) or (b[3] is not None and b[3]>=STOP_SPEED) or meters>STOP_RADIUS_M
        kind = "park" if stopped and seconds<=MAX_PARKED_GAP else "move" if moving and seconds<=MAX_MOVING_GAP and meters/seconds<90 else "unknown"
        edges.append({"a":a,"b":b,"seconds":seconds,"meters":meters,"kind":kind})
    motion=[i for i,e in enumerate(edges) if e["kind"]=="move"]
    if not motion:
        return {"empty":True,"points":[],"stops":[],"move_count":0}
    edges=edges[motion[0]:motion[-1]+1]
    stops=[]; group=[]
    def finish():
        if group and sum(e["seconds"] for e in group)>=MIN_STOP_SECONDS:
            start,end=group[0]["a"],group[-1]["b"]
            stops.append({"from":start[0],"to":end[0],"seconds":round(end[0]-start[0]),"latitude":start[1],"longitude":start[2],"estimated":any(e["seconds"]>MAX_MOVING_GAP for e in group)})
        group.clear()
    for edge in edges:
        if edge["kind"]=="park":
            # Avoid calling slow drift across a large area one stationary stop.
            if group and distance(group[0]["a"],edge["b"])>STOP_RADIUS_M:
                finish()
            group.append(edge)
        else:
            finish()
    finish()
    pause=sum(s["seconds"] for s in stops)
    unknown=sum(e["seconds"] for e in edges if e["kind"]=="unknown")
    elapsed=edges[-1]["b"][0]-edges[0]["a"][0]
    drive=max(0,elapsed-pause-unknown)
    meters=0; geodesic=False; incomplete=False
    for edge in edges:
        a,b=edge["a"],edge["b"]
        delta=b[4]-a[4] if a[4] is not None and b[4] is not None else None
        if delta is not None and 0<=delta<=edge["seconds"]*90:
            meters+=delta
        elif edge["kind"]=="move":
            meters+=edge["meters"];geodesic=True
        elif edge["kind"]=="unknown":
            incomplete=True
    return {"empty":False,"from":edges[0]["a"][0],"to":edges[-1]["b"][0],
            "drive_seconds":round(drive),"pause_seconds":round(pause),"unknown_seconds":round(unknown),
            "distance_km":round(meters/1000,1),"distance_estimated":geodesic,"distance_incomplete":incomplete,"stops":stops,
            "trip_count":len(stops)+1,"points":[edges[0]["a"]]+[e["b"] for e in edges],
            "segments":split_edges(edges)}


def split_edges(edges):
    segments=[]; current=[]
    for edge in edges:
        if edge["kind"]=="unknown":
            if current:segments.append(current)
            current=[]
        else:
            a,b=edge["a"],edge["b"]
            if not current:current.append([a[1],a[2]])
            coord=[b[1],b[2]]
            if coord!=current[-1]:current.append(coord)
    if current:segments.append(current)
    return segments


def simplify(segments, limit=1200):
    """Bounded Visvalingam-style simplification, preserving sharp corners.

    Heap update is O(n log n), keeping endpoints of every segment. Runs once in
    backend; browser never receives the 20,000+ full position records.
    """
    import heapq
    if len(segments)>limit//2:
        raise ValueError("Too many disconnected segments")
    arrays=[]; heap=[]; remaining=0
    def area(arr,i):
        p,n=arr[i][1:3]
        if p is None or n is None:return float("inf")
        a,b,c=arr[p][0],arr[i][0],arr[n][0]
        return abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
    for s,segment in enumerate(segments):
        arr=[[point,i-1 if i else None,i+1 if i+1<len(segment) else None,0,True] for i,point in enumerate(segment)]
        arrays.append(arr);remaining+=len(arr)
        for i in range(1,len(arr)-1):heapq.heappush(heap,(area(arr,i),s,i,0))
    while remaining>limit and heap:
        _,s,i,version=heapq.heappop(heap);arr=arrays[s];node=arr[i]
        if not node[4] or node[3]!=version:continue
        p,n=node[1:3];node[4]=False;remaining-=1
        arr[p][2]=n;arr[n][1]=p
        for j in (p,n):
            arr[j][3]+=1
            if arr[j][1] is not None and arr[j][2] is not None:
                heapq.heappush(heap,(area(arr,j),s,j,arr[j][3]))
    return [[[round(p[0],6),round(p[1],6)] for p,_,_,_,alive in arr if alive] for arr in arrays]
