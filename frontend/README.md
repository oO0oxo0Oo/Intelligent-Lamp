# 米家台灯传感器中控台

基于 Vue 3、TypeScript、Vite 搭建的网页端后台展示界面。当前使用静态 mock 数据渲染光照、湿度、温度、距离、亮度等传感器指标，并预留后端联调接口层。

## 启动

```bash
npm install
npm run dev
```

## 构建

```bash
npm run build
```

## 后端 JSON 结构

页面通过 `src/api/sensorService.ts` 获取数据，后续联调时将 `getSensorDashboard` 内的 mock 替换为真实 `fetch` 即可。

```ts
interface SensorDashboardPayload {
  lamp: {
    name: string
    room: string
    online: boolean
    mode: string
    colorTemperature: number
    brightness: number
    updatedAt: string
  }
  readings: Array<{
    key: 'illumination' | 'humidity' | 'temperature' | 'distance' | 'brightness'
    label: string
    value: number
    unit: string
    status: 'low' | 'normal' | 'high'
    trend: string
    description: string
  }>
}
```
