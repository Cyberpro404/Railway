# 🎨 Level 10 UI Components Guide

## New Professional Components

### 1. StatCard
**Location**: `src/components/ui/StatCard.tsx`

Premium status card with trend indicators.

```tsx
<StatCard
  title="System Status"
  value={data.status}
  change={2.5}
  changeLabel="vs last hour"
  icon={<Icon />}
  color="success" // 'primary' | 'success' | 'warning' | 'critical'
/>
```

**Props**:
- `title`: String - Card label
- `value`: String/Number - Main metric
- `change`: Number (optional) - Percentage change
- `changeLabel`: String (optional) - Change context
- `icon`: ReactNode (optional) - Icon component
- `color`: 'primary' | 'success' | 'warning' | 'critical'
- `className`: String (optional)

---

### 2. AdvancedChart
**Location**: `src/components/ui/AdvancedChart.tsx`

Flexible container for chart visualizations.

```tsx
<AdvancedChart 
  title="Chart Title"
  subtitle="Optional subtitle"
  headerAction={<button>Action</button>}
  animated={true}
>
  {/* Chart content */}
</AdvancedChart>
```

**Props**:
- `title`: String - Main heading
- `children`: ReactNode - Chart content
- `subtitle`: String (optional)
- `action`: ReactNode (optional) - Footer action
- `className`: String (optional)
- `headerAction`: ReactNode (optional) - Header controls
- `animated`: Boolean (default: true)

---

### 3. StatusBadge
**Location**: `src/components/ui/StatusBadge.tsx`

Colored status indicator badge.

```tsx
<StatusBadge
  status="critical" // 'active' | 'inactive' | 'warning' | 'critical' | 'pending'
  label="Alert"
  animated={true}
  size="md" // 'sm' | 'md' | 'lg'
/>
```

**Props**:
- `status`: Status type
- `label`: String - Badge text
- `animated`: Boolean (optional, default: true)
- `size`: 'sm' | 'md' | 'lg' (default: 'md')

---

### 4. DataTable
**Location**: `src/components/ui/DataTable.tsx`

Professional data table with custom rendering.

```tsx
<DataTable
  columns={[
    { key: 'name', label: 'Name' },
    { 
      key: 'status', 
      label: 'Status',
      render: (value) => <StatusBadge status={value} label={value} />
    }
  ]}
  data={items}
  keyExtractor={(item) => item.id}
  striped={true}
  hoverable={true}
/>
```

**Props**:
- `columns`: Column[] - Column definitions
- `data`: T[] - Data rows
- `keyExtractor`: Function - Unique key for each row
- `className`: String (optional)
- `striped`: Boolean (default: true)
- `hoverable`: Boolean (default: true)

---

## CSS Utilities

### Glassmorphism
```tsx
<div className="glassmorphism">Glass effect</div>
<div className="glassmorphism-dark">Dark glass effect</div>
```

### Neon Effects
```tsx
<div className="neon-glow">Cyan glow</div>
<div className="neon-glow-strong">Strong glow</div>
<div className="neon-glow-hover">Glow on hover</div>
<div className="neon-border">Neon border</div>
```

### Card Effects
```tsx
<div className="card-hover">Elevates on hover</div>
<div className="card-glow">Glowing card</div>
```

### Animations
```tsx
<div className="animate-bounce-in">Bounce in</div>
<div className="animate-float">Float animation</div>
<div className="animate-slideInX">Slide in X</div>
<div className="animate-glow">Glowing animation</div>
<div className="pulse-ring">Pulse ring effect</div>
<div className="shimmer">Shimmer effect</div>
<div className="float-animation">Float effect</div>
```

---

## Color System

### Usage
```tsx
{/* Background */}
bg-background        // #0A0F1A
bg-card             // #1A2332

{/* Text */}
text-text           // #E5E7EB
text-text-muted     // #9CA3AF

{/* Status */}
bg-primary/20       // Cyan with opacity
bg-success/20       // Green with opacity
bg-warning/20       // Amber with opacity
bg-critical/20      // Red with opacity

{/* Borders */}
border-border       // #2D3748
border-primary      // Cyan
border-success      // Green
border-warning      // Amber
border-critical     // Red
```

---

## Typography

### Sizes
```tsx
text-h1   // 40px, 800 weight
text-h2   // 28px, 700 weight
text-h3   // 20px, 600 weight
text-body // 16px, 400 weight
text-sm   // 14px, 400 weight
text-xs   // 12px, 500 weight
```

### Font Families
```tsx
font-sans    // Sora, Inter
font-mono    // JetBrains Mono
font-display // Sora, Inter
```

---

## Common Patterns

### Header with Accent Bar
```tsx
<div className="flex items-center gap-3 mb-2">
  <div className="w-1 h-8 bg-gradient-to-b from-primary to-primary/50 rounded-full" />
  <h1 className="text-4xl font-bold text-text tracking-tight">Title</h1>
</div>
```

### KPI Grid
```tsx
<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
  <StatCard title="Metric 1" value={100} color="primary" />
  <StatCard title="Metric 2" value={200} color="success" />
  <StatCard title="Metric 3" value={300} color="warning" />
  <StatCard title="Metric 4" value={400} color="critical" />
</div>
```

### Chart Container
```tsx
<AdvancedChart 
  title="Data Visualization"
  subtitle="Last 24 hours"
  headerAction={<button>Export</button>}
>
  <ResponsiveContainer width="100%" height={300}>
    <LineChart data={data}>
      {/* Chart content */}
    </LineChart>
  </ResponsiveContainer>
</AdvancedChart>
```

### Alert List
```tsx
{items.map((item) => (
  <div key={item.id} className="bg-background/50 border border-border/50 rounded-lg p-4 hover:border-primary/40 transition-all">
    <div className="flex items-start justify-between">
      <div>
        <p className="font-semibold text-text">{item.title}</p>
        <p className="text-sm text-text-muted mt-1">{item.description}</p>
      </div>
      <StatusBadge status={item.status} label={item.status.toUpperCase()} />
    </div>
  </div>
))}
```

---

## Pro Tips

1. **Hover Effects**: Always add `card-hover` to interactive cards
2. **Status Colors**: Use StatusBadge for consistency across the app
3. **Charts**: Wrap with AdvancedChart for uniform styling
4. **Data Tables**: Use DataTable for professional data display
5. **Animations**: Apply `animate-in fade-in duration-500` on page load
6. **Spacing**: Use multiples of 4 (p-4, gap-4, etc.)
7. **Icons**: Use lucide-react icons with 4x4, 5x5, or 6x6 sizes
8. **Gradients**: Use `from-*/to-*` utilities for color gradients

---

## Animation Timing Reference

- **Fast**: 150-200ms (micro-interactions)
- **Standard**: 300ms (hover effects, transitions)
- **Medium**: 500ms (page entry, modal)
- **Slow**: 2000ms (looping animations)

Example: `transition-all duration-300 ease-out`

---

**Version**: 4.0.0 Professional Edition ✨
