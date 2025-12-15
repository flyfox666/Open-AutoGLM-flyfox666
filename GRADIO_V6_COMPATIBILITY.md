# Gradio 6.1.0 兼容性说明

## 主要变更

本版本已针对 Gradio 6.1.0 进行了优化和兼容性修复。

### 已修复的问题

1. **移除不支持的参数**
   - 移除了 `show_copy_button=True`（在较新版本中可能被移除）
   - 移除了 `autoscroll=True`（功能已通过 JavaScript 实现）
   - 移除了 `container=True`（可能导致警告）

2. **JavaScript 兼容性**
   - 更新了 DOM 选择器，支持 Gradio 6.x 的元素结构
   - 添加了多种选择器回退方案
   - 实现了复制功能的降级方案

3. **启动参数**
   - 移除了可能引发警告的 launch() 参数
   - 添加了版本兼容性注释

### 新增特性

1. **三列式布局**
   - 左列：设备管理和无线调试
   - 中列：命令执行控制
   - 右列：参数配置和实用工具
   - 底部：宽屏日志区域

2. **增强的无线调试功能**
   - 默认展开的无线调试面板
   - 一键 USB 转无线功能
   - 设备状态实时显示

3. **改进的日志系统**
   - 通过 JavaScript 实现自动滚动
   - 智能复制功能（支持多种选择器）
   - 降级方案确保兼容性

### 注意事项

1. **自动滚动**
   - 不再使用 `autoscroll=True` 参数
   - 通过 JavaScript 每 200ms 检查并滚动到最新位置
   - 兼容 Gradio 6.x 的 DOM 结构

2. **复制功能**
   - 使用多种 DOM 选择器确保功能正常
   - 包含 `navigator.clipboard` 和降级方案
   - 提供友好的错误提示

3. **主题和样式**
   - Gradio 6.x 中 `theme` 参数已移到 `Blocks()` 构造函数
   - CSS 样式应通过其他方式注入

### 故障排除

如果遇到问题，请尝试：

1. **检查 Gradio 版本**
   ```bash
   pip show gradio
   ```

2. **升级到最新版本**
   ```bash
   pip install --upgrade gradio
   ```

3. **清理缓存**
   - 删除浏览器缓存
   - 重启 Python 进程

4. **检查控制台**
   - 打开浏览器开发者工具
   - 查看是否有 JavaScript 错误

### 开发者建议

1. **使用最新版本**
   - 建议使用 Gradio >= 4.44.0
   - 定期检查 Gradio 更新

2. **测试所有功能**
   - 无线调试
   - 日志复制
   - 自动滚动
   - 设备管理

3. **监控警告信息**
   - 启动时的警告信息应及时处理
   - 不建议忽略参数警告

## 技术细节

### DOM 选择器策略

```javascript
// 多种选择器确保兼容性
let el = document.querySelector('#log-window textarea');
if (!el) {
    el = document.querySelector('#log-window');
}
if (!el) {
    el = document.querySelector('[data-testid="log-window"] textarea');
}
if (!el) {
    el = document.querySelector('[data-testid="log-window"]');
}
```

### 复制功能降级

```javascript
// 首选方法
navigator.clipboard.writeText(text)
    .catch(() => {
        // 降级方法
        document.execCommand('copy');
    });
```

### 自动滚动实现

```javascript
// 定时检查并滚动
setTimeout(() => {
    if (el && el.scrollTop !== undefined) {
        el.scrollTop = el.scrollHeight;
    }
}, 50);
```