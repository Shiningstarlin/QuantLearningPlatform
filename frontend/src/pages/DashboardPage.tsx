import { PageHeader } from "../ui/PageHeader";

export function DashboardPage() {
  return (
    <>
      <PageHeader title="学习总览" subtitle="查看模拟资金、任务状态和近期表现。" />
      <section className="metric-grid">
        <div className="metric-card">
          <span>总模拟净值</span>
          <strong>$100,000.00</strong>
        </div>
        <div className="metric-card">
          <span>运行中任务</span>
          <strong>0</strong>
        </div>
        <div className="metric-card">
          <span>本月模拟收益</span>
          <strong>0.00%</strong>
        </div>
      </section>
    </>
  );
}
