# 蓝奏云解析插件

一个用于 AstrBot 的蓝奏云文件解析插件，支持自动检测和手动解析蓝奏云分享链接。

## 功能特性

- 🔍 **自动检测**：自动识别消息中的蓝奏云链接并解析
- 📝 **手动解析**：通过 `/lanzou` 命令手动解析链接
- 🔐 **密码支持**：支持带密码的蓝奏云链接
- 📊 **详细信息**：显示文件名、文件大小和直链下载地址
- ⚡ **异步处理**：基于异步HTTP请求，响应速度快

## 使用方法

### 手动解析
使用指令 `/lanzou` 来解析蓝奏云链接：

```
/lanzou https://www.lanzoup.com/ixxxxxx
/lanzou https://www.lanzoup.com/ixxxxxx 密码
```

**注意：** 目前仅支持手动指令解析，暂不支持自动检测功能。

## 支持的域名

- lanzoup.com
- lanzoug.com
- lanzous.com
- 以及其他 lanzou 系列域名

## 安装依赖

插件依赖 `httpx` 库，安装插件时会自动安装依赖。

## 技术特性

- 支持带密码和不带密码的蓝奏云链接
- 自动处理重定向和最终下载链接
- 随机IP和User-Agent，提高解析成功率
- 完善的错误处理和日志记录

## 支持

- [AstrBot 官方文档](https://astrbot.app)
- [插件开发文档](https://astrbot.app/dev/star/plugin.html)
- [开发者联系方式](https://qm.qq.com/q/nDHgJBm5Mc)
- [插件反馈群](https://qm.qq.com/q/d4lwUp9ap4)

## 许可证

本项目基于 GPL-3.0 许可证开源。
