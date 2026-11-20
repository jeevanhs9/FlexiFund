import { formatCompactMoney, formatMoney } from "./utils.js";

const CATEGORY_COLORS = ["#2f7b57", "#7ea88c", "#c8a568", "#7d8fb1", "#c98270", "#a49a70", "#6b9da2", "#b27c99", "#8d967f", "#a9865d", "#718c78"];

function EmptyChart({ children = "Add records to see this chart." }) {
  return <div className="p3-chart-empty">{children}</div>;
}

export function MonthlyTrendChart({ rows = [] }) {
  if (!rows.length) return <EmptyChart>No monthly data available yet.</EmptyChart>;

  const width = 760;
  const height = 300;
  const pad = { top: 22, right: 18, bottom: 48, left: 58 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const maxValue = Math.max(1, ...rows.map((row) => Math.max(Number(row.income), Number(row.expenses))));
  const minSurplus = Math.min(0, ...rows.map((row) => Number(row.surplus)));
  const domainMin = minSurplus < 0 ? minSurplus * 1.15 : 0;
  const domainMax = maxValue * 1.12;
  const valueToY = (value) => pad.top + ((domainMax - value) / (domainMax - domainMin)) * plotHeight;
  const zeroY = valueToY(0);
  const slot = plotWidth / rows.length;
  const barWidth = Math.min(26, Math.max(8, slot * 0.23));
  const surplusPath = rows.map((row, index) => {
    const x = pad.left + slot * index + slot / 2;
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${valueToY(Number(row.surplus)).toFixed(1)}`;
  }).join(" ");
  const gridValues = [0, domainMax / 2, domainMax];

  return (
    <div className="p3-chart-scroll">
      <div className="p3-chart-legend" aria-label="Chart legend">
        <span><i className="legend-income" />Income</span>
        <span><i className="legend-expenses" />Expenses</span>
        <span><i className="legend-surplus" />Surplus</span>
      </div>
      <svg className="p3-trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Monthly income, expenses, and surplus from the FlexiFund API">
        {gridValues.map((value) => {
          const y = valueToY(value);
          return <g key={value}><line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className={value === 0 ? "p3-chart-zero" : "p3-chart-grid"} /><text x={pad.left - 9} y={y + 4} textAnchor="end" className="p3-chart-label">{formatCompactMoney(value)}</text></g>;
        })}
        {rows.map((row, index) => {
          const center = pad.left + slot * index + slot / 2;
          const income = Number(row.income);
          const expenses = Number(row.expenses);
          const incomeY = valueToY(income);
          const expensesY = valueToY(expenses);
          return (
            <g key={`${row.year}-${row.month}`}>
              <title>{`${row.month} ${row.year}: income ${formatMoney(income)}, expenses ${formatMoney(expenses)}, surplus ${formatMoney(row.surplus)}`}</title>
              <rect x={center - barWidth - 3} y={Math.min(incomeY, zeroY)} width={barWidth} height={Math.max(1, Math.abs(zeroY - incomeY))} rx="4" className="p3-bar-income" />
              <rect x={center + 3} y={Math.min(expensesY, zeroY)} width={barWidth} height={Math.max(1, Math.abs(zeroY - expensesY))} rx="4" className="p3-bar-expenses" />
              <text x={center} y={height - 18} textAnchor="middle" className="p3-chart-label">{row.month.slice(0, 3)}</text>
            </g>
          );
        })}
        <path d={surplusPath} className="p3-surplus-path" />
        {rows.map((row, index) => {
          const center = pad.left + slot * index + slot / 2;
          return <circle key={`surplus-${row.year}-${row.month}`} cx={center} cy={valueToY(Number(row.surplus))} r="4" className="p3-surplus-dot"><title>{`${row.month} surplus ${formatMoney(row.surplus)}`}</title></circle>;
        })}
      </svg>
    </div>
  );
}

export function SavingsTrendChart({ rows = [] }) {
  if (!rows.length) return <EmptyChart>No savings history available yet.</EmptyChart>;

  const width = 700;
  const height = 230;
  const pad = { top: 20, right: 18, bottom: 40, left: 60 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const values = rows.map((row) => Number(row.surplus));
  const maxValue = Math.max(1, ...values, 0);
  const minValue = Math.min(0, ...values);
  const rangeMin = minValue < 0 ? minValue * 1.12 : 0;
  const rangeMax = maxValue * 1.12;
  const xAt = (index) => pad.left + (rows.length === 1 ? plotWidth / 2 : (index / (rows.length - 1)) * plotWidth);
  const yAt = (value) => pad.top + ((rangeMax - value) / (rangeMax - rangeMin)) * plotHeight;
  const path = values.map((value, index) => `${index === 0 ? "M" : "L"} ${xAt(index).toFixed(1)} ${yAt(value).toFixed(1)}`).join(" ");
  const guides = [0, rangeMax / 2, rangeMax];

  return (
    <div className="p3-chart-scroll">
      <svg className="p3-savings-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Monthly surplus and savings trend from the FlexiFund API">
        {guides.map((value) => <g key={value}><line x1={pad.left} x2={width - pad.right} y1={yAt(value)} y2={yAt(value)} className="p3-chart-grid" /><text x={pad.left - 8} y={yAt(value) + 4} textAnchor="end" className="p3-chart-label">{formatCompactMoney(value)}</text></g>)}
        <path d={path} className="p3-savings-path" />
        {rows.map((row, index) => <g key={`${row.year}-${row.month}`}><circle cx={xAt(index)} cy={yAt(Number(row.surplus))} r="4" className="p3-savings-dot"><title>{`${row.month} ${row.year}: ${formatMoney(row.surplus)} remaining`}</title></circle><text x={xAt(index)} y={height - 14} textAnchor="middle" className="p3-chart-label">{row.month.slice(0, 3)}</text></g>)}
      </svg>
    </div>
  );
}

export function ExpenseDonutChart({ categories = {} }) {
  const entries = Object.entries(categories)
    .map(([name, value]) => [name, Number(value)])
    .filter(([, value]) => Number.isFinite(value) && value > 0);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);
  if (!entries.length || total <= 0) return <EmptyChart>No expense categories in this period.</EmptyChart>;

  const radius = 66;
  const circumference = 2 * Math.PI * radius;
  let consumed = 0;

  return (
    <div className="p3-donut-layout">
      <div className="p3-donut-visual">
        <svg viewBox="0 0 180 180" role="img" aria-label={`Expense category breakdown totalling ${formatMoney(total)}`}>
          <circle cx="90" cy="90" r={radius} className="p3-donut-track" />
          {entries.map(([name, value], index) => {
            const segment = (value / total) * circumference;
            const offset = consumed;
            consumed += segment;
            return <circle key={name} cx="90" cy="90" r={radius} fill="none" stroke={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} strokeWidth="24" strokeDasharray={`${segment} ${circumference - segment}`} strokeDashoffset={-offset} transform="rotate(-90 90 90)" className="p3-donut-segment"><title>{`${name}: ${formatMoney(value)} (${((value / total) * 100).toFixed(1)}%)`}</title></circle>;
          })}
          <text x="90" y="84" textAnchor="middle" className="p3-donut-total-label">TOTAL</text>
          <text x="90" y="105" textAnchor="middle" className="p3-donut-total">{formatMoney(total)}</text>
        </svg>
      </div>
      <ul className="p3-donut-legend">
        {entries.map(([name, value], index) => <li key={name}><span className="p3-legend-swatch" style={{ backgroundColor: CATEGORY_COLORS[index % CATEGORY_COLORS.length] }} /><span className="p3-legend-name">{name}</span><strong>{formatMoney(value)}</strong></li>)}
      </ul>
    </div>
  );
}

export function ExpenseComparison({ essential = 0, nonEssential = 0 }) {
  const essentialValue = Number(essential) || 0;
  const nonEssentialValue = Number(nonEssential) || 0;
  const total = essentialValue + nonEssentialValue;
  const essentialPercent = total > 0 ? (essentialValue / total) * 100 : 0;
  const nonEssentialPercent = total > 0 ? (nonEssentialValue / total) * 100 : 0;

  return (
    <div className="p3-comparison">
      <div className="p3-comparison-row">
        <div className="p3-comparison-copy"><span>Essential</span><strong>{formatMoney(essentialValue)}</strong><small>{essentialPercent.toFixed(1)}%</small></div>
        <div className="p3-comparison-track" role="img" aria-label={`Essential expenses are ${essentialPercent.toFixed(1)} percent of classified expenses`}><span className="p3-comparison-fill essential-fill" style={{ width: `${essentialPercent}%` }} /></div>
      </div>
      <div className="p3-comparison-row">
        <div className="p3-comparison-copy"><span>Non-essential</span><strong>{formatMoney(nonEssentialValue)}</strong><small>{nonEssentialPercent.toFixed(1)}%</small></div>
        <div className="p3-comparison-track" role="img" aria-label={`Non-essential expenses are ${nonEssentialPercent.toFixed(1)} percent of classified expenses`}><span className="p3-comparison-fill nonessential-fill" style={{ width: `${nonEssentialPercent}%` }} /></div>
      </div>
      {total === 0 && <EmptyChart>No classified expenses in this period.</EmptyChart>}
    </div>
  );
}
