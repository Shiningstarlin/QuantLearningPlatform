# Frontend

React + Vite frontend for the simulated quantitative trading learning platform.

## Routes

| Route | Purpose |
|---|---|
| `/login` | login |
| `/register` | register |
| `/dashboard` | overview |
| `/market-board` | realtime/recent market quote board |
| `/market-board/:assetId` | market asset detail with intraday/daily/weekly/monthly chart |
| `/tasks` | simulation task list |
| `/tasks/new` | create task |
| `/tasks/:taskId` | task detail and controls |
| `/tasks/:taskId/assets` | watched assets |
| `/tasks/:taskId/logs` | paper trade logs |
| `/tasks/:taskId/analytics` | daily/monthly analytics |
| `/settings` | user and simulation defaults |

## Run

```bash
cd frontend
npm install
npm run dev
```
