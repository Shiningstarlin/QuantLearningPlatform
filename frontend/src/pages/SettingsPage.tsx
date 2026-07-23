import { PageHeader } from "../ui/PageHeader";

export function SettingsPage() {
  return (
    <>
      <PageHeader title="设置" subtitle="配置默认币种、行情来源、税费默认值和学习偏好。" />
      <div className="form-panel">
        <label>
          默认基础货币
          <select defaultValue="USD">
            <option value="USD">USD</option>
            <option value="CNY">CNY</option>
          </select>
        </label>
        <label className="checkbox-label">
          <input type="checkbox" defaultChecked />
          默认启用 T+1
        </label>
      </div>
    </>
  );
}
