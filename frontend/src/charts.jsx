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

export function ForecastChart({ rows = [], forecast = {} }) {
  const actual = rows.slice(-6);
  if (!actual.length && !forecast.available) {
    return <EmptyChart>Add financial transactions to unlock financial intelligence.</EmptyChart>;
  }
  const displayRows = [...actual, ...(forecast.available ? [{
    year: Number(String(forecast.forecast_period).slice(0, 4)),
    month_number: Number(String(forecast.forecast_period).slice(5, 7)),
    month: forecast.forecast_month,
    total_income: forecast.predicted_income,
    total_expenses: forecast.predicted_expenses,
    total_savings: forecast.predicted_savings,
    predicted: true,
  }] : [])];
  const width = 720;
  const height = 320;
  const pad = { top: 30, right: 16, bottom: 50, left: 60 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const maxValue = Math.max(1, ...displayRows.map((row) => Math.max(Number(row.total_income) || 0, Number(row.total_expenses) || 0)));
  const minValue = Math.min(0, ...(forecast.available ? [Number(forecast.predicted_savings) || 0] : []));
  const domainMin = minValue * 1.1;
  const domainMax = maxValue * 1.15;
  const yAt = (value) => pad.top + ((domainMax - (Number(value) || 0)) / (domainMax - domainMin)) * plotHeight;
  const zeroY = yAt(0);
  const gridValues = [...new Set([domainMin, 0, domainMax])];
  const slot = plotWidth / displayRows.length;
  const barWidth = Math.min(23, Math.max(9, slot * 0.22));

  // Create area paths for income and expenses
  const incomeAreaPath = displayRows.map((row, i) => {
    const x = pad.left + slot * i + slot / 2;
    const y = yAt(row.total_income);
    return i === 0 ? `M ${x} ${zeroY} L ${x} ${y}` : `L ${x} ${y}`;
  }).join(" ") + ` L ${pad.left + slot * (displayRows.length - 1) + slot / 2} ${zeroY} Z`;

  const expenseAreaPath = displayRows.map((row, i) => {
    const x = pad.left + slot * i + slot / 2;
    const y = yAt(row.total_expenses);
    return i === 0 ? `M ${x} ${zeroY} L ${x} ${y}` : `L ${x} ${y}`;
  }).join(" ") + ` L ${pad.left + slot * (displayRows.length - 1) + slot / 2} ${zeroY} Z`;

  // Create line paths
  const incomePath = displayRows.map((row, i) => {
    const x = pad.left + slot * i + slot / 2;
    const y = yAt(row.total_income);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");

  const expensePath = displayRows.map((row, i) => {
    const x = pad.left + slot * i + slot / 2;
    const y = yAt(row.total_expenses);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");

  // Confidence band for forecast (if available)
  let confidenceBand = null;
  if (forecast.available && displayRows.length > 0) {
    const forecastIndex = displayRows.length - 1;
    const x = pad.left + slot * forecastIndex + slot / 2;
    const incomeY = yAt(forecast.predicted_income);
    const expenseY = yAt(forecast.predicted_expenses);
    const uncertainty = 0.15; // 15% uncertainty band
    
    confidenceBand = {
      income: {
        x,
        yTop: yAt(forecast.predicted_income * (1 + uncertainty)),
        yBottom: yAt(forecast.predicted_income * (1 - uncertainty)),
      },
      expense: {
        x,
        yTop: yAt(forecast.predicted_expenses * (1 + uncertainty)),
        yBottom: yAt(forecast.predicted_expenses * (1 - uncertainty)),
      }
    };
  }

  return (
    <div className="p3-chart-scroll">
      <div className="p3-chart-legend forecast-legend" aria-label="Forecast chart legend">
        <span><i className="legend-income" />Income</span>
        <span><i className="legend-expenses" />Expenses</span>
        {forecast.available && <span><i className="legend-forecast" />Forecast</span>}
      </div>
      <svg className="p3-forecast-chart forecast-chart-enhanced" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={forecast.available ? "Historical actual income and expenses with a visibly distinct next-month forecast" : "Historical actual income and expenses; forecast unavailable"}>
        <defs>
          <linearGradient id="incomeGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(67, 142, 97, 0.3)" />
            <stop offset="100%" stopColor="rgba(67, 142, 97, 0.05)" />
          </linearGradient>
          <linearGradient id="expenseGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(196, 165, 110, 0.25)" />
            <stop offset="100%" stopColor="rgba(196, 165, 110, 0.05)" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Grid lines */}
        {gridValues.map((value) => {
          const y = yAt(value);
          return <g key={value}>
            <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className={value === 0 ? "p3-chart-zero" : "p3-chart-grid"} />
            <text x={pad.left - 8} y={y + 4} textAnchor="end" className="p3-chart-label">{formatCompactMoney(value)}</text>
          </g>;
        })}

        {/* Area fills with animation */}
        <path d={incomeAreaPath} className="forecast-area-income" fill="url(#incomeGradient)" />
        <path d={expenseAreaPath} className="forecast-area-expense" fill="url(#expenseGradient)" />

        {/* Confidence bands for forecast */}
        {confidenceBand && (
          <>
            <rect 
              x={confidenceBand.income.x - 15} 
              y={confidenceBand.income.yTop} 
              width="30" 
              height={confidenceBand.income.yBottom - confidenceBand.income.yTop}
              className="forecast-confidence-band income-band"
              rx="4"
            />
            <rect 
              x={confidenceBand.expense.x - 15} 
              y={confidenceBand.expense.yTop} 
              width="30" 
              height={confidenceBand.expense.yBottom - confidenceBand.expense.yTop}
              className="forecast-confidence-band expense-band"
              rx="4"
            />
          </>
        )}

        {/* Line paths with animation */}
        <path d={incomePath} className="forecast-line-income" strokeWidth="2.5" fill="none" />
        <path d={expensePath} className="forecast-line-expense" strokeWidth="2.5" fill="none" />

        {/* Data points with hover effects */}
        {displayRows.map((row, index) => {
          const center = pad.left + slot * index + slot / 2;
          const incomeY = yAt(row.total_income);
          const expenseY = yAt(row.total_expenses);
          const savingsY = yAt(row.total_savings);
          const isPredicted = row.predicted;
          
          return (
            <g key={`${row.year}-${row.month_number}-${row.predicted ? "forecast" : "actual"}`} className={isPredicted ? "forecast-predicted-group" : "forecast-actual-group"}>
              <title>{`${row.predicted ? "Predicted" : "Actual"} ${row.month} ${row.year}: income ${formatMoney(row.total_income)}, expenses ${formatMoney(row.total_expenses)}${row.predicted ? `, savings ${formatMoney(row.total_savings)}` : ""}`}</title>
              
              {/* Income point */}
              <circle cx={center} cy={incomeY} r={isPredicted ? "6" : "5"} className={isPredicted ? "forecast-point-predicted income-point" : "forecast-point income-point"} filter={isPredicted ? "url(#glow)" : ""} />
              
              {/* Expense point */}
              <circle cx={center} cy={expenseY} r={isPredicted ? "6" : "5"} className={isPredicted ? "forecast-point-predicted expense-point" : "forecast-point expense-point"} filter={isPredicted ? "url(#glow)" : ""} />
              
              {/* Savings point for forecast */}
              {isPredicted && (
                <circle cx={center} cy={savingsY} r="6" className="forecast-point-predicted savings-point" filter="url(#glow)" />
              )}
              
              {/* Vertical connector line for predicted */}
              {isPredicted && (
                <line 
                  x1={center} 
                  y1={Math.min(incomeY, expenseY, savingsY)} 
                  x2={center} 
                  y2={Math.max(incomeY, expenseY, savingsY)} 
                  className="forecast-connector"
                  strokeDasharray="2 2"
                />
              )}
              
              {/* Month label */}
              <text x={center} y={height - 20} textAnchor="middle" className="p3-chart-label forecast-label">
                {row.month.slice(0, 3)}
                {isPredicted && <tspan className="forecast-asterisk">*</tspan>}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="p3-chart-note">{forecast.available ? `* ${forecast.forecast_month} is a ${forecast.confidence}-confidence statistical estimate with uncertainty bands shown.` : forecast.explanation || "Forecast unavailable."}</p>
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

export function CashFlowWaterfallChart({ forecast = {} }) {
  if (!forecast.available) {
    return <EmptyChart>Forecast data required for waterfall visualization.</EmptyChart>;
  }

  const income = Number(forecast.predicted_income) || 0;
  const expenses = Number(forecast.predicted_expenses) || 0;
  const savings = Number(forecast.predicted_savings) || 0;

  const width = 720;
  const height = 280;
  const pad = { top: 30, right: 20, bottom: 50, left: 70 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;

  const maxValue = Math.max(income, income - expenses, savings) * 1.15;
  const minValue = Math.min(0, savings) * 1.1;
  const yAt = (value) => pad.top + ((maxValue - value) / (maxValue - minValue)) * plotHeight;

  const barWidth = 50;
  const gap = (plotWidth - barWidth * 3) / 2;

  const steps = [
    { label: "Income", value: income, x: pad.left, color: "#438e61", type: "positive" },
    { label: "Expenses", value: -expenses, x: pad.left + barWidth + gap, color: "#c4a56e", type: "negative", base: income },
    { label: "Savings", value: savings, x: pad.left + (barWidth + gap) * 2, color: savings >= 0 ? "#2f7b57" : "#b45c53", type: "result" },
  ];

  return (
    <div className="p3-chart-scroll">
      <svg className="waterfall-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Cash flow waterfall for ${forecast.forecast_month}`}>
        <defs>
          <linearGradient id="waterfallIncome" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#438e61" stopOpacity="1" />
            <stop offset="100%" stopColor="#2f7b57" stopOpacity="1" />
          </linearGradient>
          <linearGradient id="waterfallExpense" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#c4a56e" stopOpacity="1" />
            <stop offset="100%" stopColor="#a8865d" stopOpacity="1" />
          </linearGradient>
          <linearGradient id="waterfallSavings" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={savings >= 0 ? "#2f7b57" : "#b45c53"} stopOpacity="1" />
            <stop offset="100%" stopColor={savings >= 0 ? "#1f5a3d" : "#8d3d36"} stopOpacity="1" />
          </linearGradient>
        </defs>

        {/* Zero line */}
        <line x1={pad.left} x2={width - pad.right} y1={yAt(0)} y2={yAt(0)} className="p3-chart-zero waterfall-zero" strokeWidth="1.5" />

        {/* Grid lines */}
        {[0, maxValue / 2, maxValue].map((value) => {
          const y = yAt(value);
          return value !== 0 && (
            <g key={value}>
              <line x1={pad.left} x2={width - pad.right} y1={y} y2={y} className="p3-chart-grid" opacity="0.3" />
              <text x={pad.left - 8} y={y + 4} textAnchor="end" className="p3-chart-label">{formatCompactMoney(value)}</text>
            </g>
          );
        })}

        {/* Connector lines between bars */}
        <line 
          x1={steps[0].x + barWidth} 
          y1={yAt(income)} 
          x2={steps[1].x} 
          y2={yAt(income)}
          className="waterfall-connector"
          strokeDasharray="4 2"
        />
        <line 
          x1={steps[1].x + barWidth} 
          y1={yAt(income - expenses)} 
          x2={steps[2].x} 
          y2={yAt(income - expenses)}
          className="waterfall-connector"
          strokeDasharray="4 2"
        />

        {/* Bars */}
        {steps.map((step, index) => {
          let barY, barHeight;
          const zeroY = yAt(0);
          
          if (step.type === "positive") {
            barY = yAt(step.value);
            barHeight = zeroY - barY;
          } else if (step.type === "negative") {
            const baseY = yAt(step.base);
            const endY = yAt(step.base + step.value);
            barY = Math.min(baseY, endY);
            barHeight = Math.abs(endY - baseY);
          } else {
            barY = yAt(Math.max(0, step.value));
            barHeight = Math.abs(yAt(step.value) - zeroY);
          }

          const fillUrl = index === 0 ? "url(#waterfallIncome)" : index === 1 ? "url(#waterfallExpense)" : "url(#waterfallSavings)";

          return (
            <g key={step.label} className="waterfall-bar-group">
              <title>{`${step.label}: ${formatMoney(Math.abs(step.value))}`}</title>
              
              {/* Bar */}
              <rect
                x={step.x}
                y={barY}
                width={barWidth}
                height={barHeight}
                rx="6"
                fill={fillUrl}
                className="waterfall-bar"
              />
              
              {/* Value label on bar */}
              <text
                x={step.x + barWidth / 2}
                y={barY - 8}
                textAnchor="middle"
                className="waterfall-value-label"
                fill="var(--text-primary)"
              >
                {formatCompactMoney(Math.abs(step.value))}
              </text>

              {/* Category label */}
              <text
                x={step.x + barWidth / 2}
                y={height - 20}
                textAnchor="middle"
                className="waterfall-category-label"
              >
                {step.label}
              </text>
            </g>
          );
        })}
      </svg>
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
