import { MouseEvent, useId, useMemo, useState } from "react";

type Point = {
  price: number;
  quote_time: string;
};

export type ChartMarker = {
  price: number;
  quote_time: string;
  side: "buy" | "sell";
  label?: string;
};

type LineChartProps = {
  points: Point[];
  markers?: ChartMarker[];
  height?: number;
  compact?: boolean;
};

export function LineChart({ points, markers = [], height = 260, compact = false }: LineChartProps) {
  const width = 760;
  const padding = compact ? { top: 8, right: 8, bottom: 8, left: 8 } : { top: 28, right: 70, bottom: 34, left: 58 };
  const rawGradientId = useId();
  const gradientId = `chart-gradient-${rawGradientId.replace(/:/g, "")}`;
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const cleanPoints = useMemo(
    () => points.filter((point) => Number.isFinite(point.price) && point.quote_time),
    [points]
  );
  const cleanMarkers = useMemo(
    () => markers.filter((marker) => Number.isFinite(marker.price) && marker.quote_time),
    [markers]
  );

  if (cleanPoints.length < 2) {
    return <div className={compact ? "chart-empty compact" : "chart-empty"}>等待更多报价</div>;
  }

  const prices = [...cleanPoints.map((point) => point.price), ...cleanMarkers.map((marker) => marker.price)];
  const rawMin = Math.min(...prices);
  const rawMax = Math.max(...prices);
  const rawSpan = rawMax - rawMin || rawMax * 0.01 || 1;
  const min = rawMin - rawSpan * 0.08;
  const max = rawMax + rawSpan * 0.08;
  const span = max - min || 1;
  const chartLeft = padding.left;
  const chartRight = width - padding.right;
  const chartTop = padding.top;
  const chartBottom = height - padding.bottom;
  const chartWidth = chartRight - chartLeft;
  const chartHeight = chartBottom - chartTop;

  const coords = cleanPoints.map((point, index) => {
    const x = chartLeft + (index / (cleanPoints.length - 1)) * chartWidth;
    const y = chartBottom - ((point.price - min) / span) * chartHeight;
    return { x, y, point };
  });
  const markerCoords = cleanMarkers.map((marker) => {
    const markerTime = new Date(marker.quote_time).getTime();
    let nearestIndex = 0;
    let nearestDistance = Number.POSITIVE_INFINITY;
    cleanPoints.forEach((point, index) => {
      const pointTime = new Date(point.quote_time).getTime();
      const distance =
        Number.isNaN(markerTime) || Number.isNaN(pointTime)
          ? Math.abs(index - nearestIndex)
          : Math.abs(pointTime - markerTime);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIndex = index;
      }
    });
    const x = coords[nearestIndex]?.x ?? chartLeft;
    const y = chartBottom - ((marker.price - min) / span) * chartHeight;
    return { ...marker, x, y };
  });

  const path = coords.map((coord, index) => `${index === 0 ? "M" : "L"} ${coord.x.toFixed(2)} ${coord.y.toFixed(2)}`).join(" ");
  const areaPath = `${path} L ${coords[coords.length - 1].x.toFixed(2)} ${chartBottom.toFixed(2)} L ${coords[0].x.toFixed(2)} ${chartBottom.toFixed(2)} Z`;
  const last = coords[coords.length - 1];
  const firstPrice = prices[0];
  const lastPrice = prices[prices.length - 1];
  const positive = lastPrice >= firstPrice;
  const trendClass = positive ? "positive" : "negative";
  const axisValues = [max, max - span / 3, max - (span / 3) * 2, min];
  const selected = hoverIndex === null ? last : coords[hoverIndex];

  function handleMove(event: MouseEvent<SVGSVGElement>) {
    if (compact) {
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * width;
    const ratio = Math.min(1, Math.max(0, (x - chartLeft) / chartWidth));
    setHoverIndex(Math.round(ratio * (coords.length - 1)));
  }

  function formatTime(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return compact ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : date.toLocaleString();
  }

  function pctLabel(value: number) {
    if (!firstPrice) {
      return "0.00%";
    }
    const pct = ((value - firstPrice) / firstPrice) * 100;
    return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
  }

  return (
    <svg
      className={compact ? `line-chart compact ${trendClass}` : `line-chart ${trendClass}`}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      onMouseMove={handleMove}
      onMouseLeave={() => setHoverIndex(null)}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity={compact ? "0.18" : "0.22"} />
          <stop offset="70%" stopColor="currentColor" stopOpacity="0.05" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>

      {!compact
        ? axisValues.map((value) => {
            const y = chartBottom - ((value - min) / span) * chartHeight;
            return (
              <g key={value.toFixed(6)}>
                <line className="chart-grid-line" x1={chartLeft} x2={chartRight} y1={y} y2={y} />
                <text className="chart-axis left" x={chartLeft - 10} y={y + 4} textAnchor="end">
                  {value.toFixed(2)}
                </text>
                <text className="chart-axis right" x={chartRight + 10} y={y + 4}>
                  {pctLabel(value)}
                </text>
              </g>
            );
          })
        : null}

      <path className="chart-area" d={areaPath} fill={`url(#${gradientId})`} />
      <path className="chart-line" d={path} />

      {!compact
        ? markerCoords.map((marker, index) => (
            <g className={`chart-trade-marker ${marker.side}`} key={`${marker.quote_time}-${marker.side}-${index}`}>
              <title>{marker.label ?? `${marker.side} ${marker.price.toFixed(2)} ${marker.quote_time}`}</title>
              {marker.side === "buy" ? (
                <path
                  d={`M ${marker.x.toFixed(2)} ${(marker.y - 9).toFixed(2)} L ${(marker.x - 7).toFixed(2)} ${(marker.y + 5).toFixed(2)} L ${(marker.x + 7).toFixed(2)} ${(marker.y + 5).toFixed(2)} Z`}
                />
              ) : (
                <path
                  d={`M ${marker.x.toFixed(2)} ${(marker.y + 9).toFixed(2)} L ${(marker.x - 7).toFixed(2)} ${(marker.y - 5).toFixed(2)} L ${(marker.x + 7).toFixed(2)} ${(marker.y - 5).toFixed(2)} Z`}
                />
              )}
            </g>
          ))
        : null}

      {!compact ? (
        <>
          {[coords[0], coords[Math.floor(coords.length / 2)], last].map((coord) => (
            <text className="chart-axis bottom" key={`${coord.x}-${coord.point.quote_time}`} x={coord.x} y={height - 8} textAnchor="middle">
              {formatTime(coord.point.quote_time)}
            </text>
          ))}
          <line className="chart-hover-line" x1={selected.x} x2={selected.x} y1={chartTop} y2={chartBottom} />
          <circle className="chart-point" cx={selected.x} cy={selected.y} r={4.5} />
          <g transform={`translate(${Math.min(selected.x + 12, chartRight - 150)} ${Math.max(selected.y - 42, chartTop + 8)})`}>
            <rect className="chart-tooltip-bg" width="138" height="38" rx="6" />
            <text className="chart-tooltip-price" x="10" y="16">
              {selected.point.price.toFixed(2)}
            </text>
            <text className="chart-tooltip-time" x="10" y="31">
              {formatTime(selected.point.quote_time)}
            </text>
          </g>
        </>
      ) : null}

      {compact ? <circle className="chart-point" cx={last.x} cy={last.y} r={3} /> : null}
    </svg>
  );
}
