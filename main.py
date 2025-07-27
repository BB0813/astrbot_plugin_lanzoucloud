from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
import re
import json
import random
from typing import Optional
from urllib.parse import urlparse

@register("lanzoucloud", "Binbim", "蓝奏云文件解析插件", "1.0.0")
class LanzouCloudPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.default_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"

    async def initialize(self):
        """插件初始化方法"""
        logger.info("蓝奏云解析插件已初始化")
    
    def rand_ip(self):
        """生成随机IP地址"""
        ip2id = round(random.randint(600000, 2550000) / 10000)
        ip3id = round(random.randint(600000, 2550000) / 10000)
        ip4id = round(random.randint(600000, 2550000) / 10000)
        arr_1 = ["218", "218", "66", "66", "218", "218", "60", "60", "202", "204", 
                 "66", "66", "66", "59", "61", "60", "222", "221", "66", "59", 
                 "60", "60", "66", "218", "218", "62", "63", "64", "66", "66", "122", "211"]
        ip1id = random.choice(arr_1)
        return f"{ip1id}.{ip2id}.{ip3id}.{ip4id}"

    def _get_domain_from_url(self, url: str) -> str:
        """安全地从URL中提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc or 'www.lanzoup.com'
        except Exception:
            return 'www.lanzoup.com'
    

    
    def _extract_file_info(self, soft_info):
        """从页面内容中提取文件信息"""
        file_info = {'name': '未知文件', 'size': '未知大小'}
        
        # 尝试多种正则表达式匹配文件名
        name_patterns = [
            r'style="font-size: 30px;text-align: center;padding: 56px 0px 20px 0px;">(.*?)</div>',
            r'<div class="n_box_3fn".*?>(.*?)</div>',
            r'var filename = \'(.*?)\';',
            r'div class="b"><span>(.*?)</span></div>'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, soft_info)
            if match:
                file_info['name'] = match.group(1)
                break
        
        # 尝试匹配文件大小
        size_patterns = [
            r'<div class="n_filesize".*?>大小：(.*?)</div>',
            r'<span class="p7">文件大小：</span>(.*?)<br>'
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, soft_info)
            if match:
                file_info['size'] = match.group(1)
                break
        
        return file_info
    
    async def _handle_password_protected_link(self, soft_info, url, pwd, file_info):
        """处理密码保护的链接"""
        if not pwd:
            raise Exception("请输入分享密码")
        
        # 提取必要参数
        segment_match = re.findall(r"'sign':'(.*?)',", soft_info)
        signs_match = re.findall(r"ajaxdata = '(.*?)'", soft_info)
        ajaxm_match = re.findall(r"ajaxm\.php\?file=(\d+)", soft_info)
        
        if not segment_match or not ajaxm_match:
            raise Exception("解析页面参数失败")
        
        post_data = {
             "action": "downprocess",
             "sign": segment_match[1] if len(segment_match) > 1 else segment_match[0],
             "p": pwd,
             "kd": 1
         }
        
        # 使用原始域名构建ajax URL
        base_domain = self._get_domain_from_url(url)
        ajax_url = f"https://{base_domain}/ajaxm.php?file={ajaxm_match[0]}"
        response = await self.mlooc_curl_post(post_data, ajax_url, url)
        
        try:
            result = json.loads(response)
            if 'inf' in result:
                file_info['name'] = result['inf']
        except json.JSONDecodeError:
            pass
        
        return response
    
    async def _handle_public_link(self, soft_info, url, file_info):
        """处理公开链接"""
        iframe_patterns = [
            r'\n<iframe.*?name="[\s\S]*?"\ssrc="\/(.*?)"',
            r'<iframe.*?name="[\s\S]*?"\ssrc="\/(.*?)"',
            r'<iframe.*?src="\/(.*?)"',
            r'<iframe[^>]*src="([^"]*?)"',
            r'src="\/(fn\?[^"]*?)"',
            r'src="([^"]*fn\?[^"]*?)"'
        ]
        
        link_match = None
        for pattern in iframe_patterns:
            link_match = re.search(pattern, soft_info)
            if link_match:
                break
        
        if not link_match:
            # 如果是文件夹链接，尝试提取文件夹信息
            if "文件夹" in soft_info or "folder" in url.lower() or "/b" in url:
                raise Exception("检测到文件夹链接，请提供具体文件的分享链接")
            else:
                raise Exception("无法解析iframe链接，请检查链接是否正确")
        
        # 构建iframe URL，使用原始域名
        iframe_path = link_match.group(1)
        base_domain = self._get_domain_from_url(url)
        
        if iframe_path.startswith('http'):
            ifurl = iframe_path
        elif iframe_path.startswith('/'):
            ifurl = f"https://{base_domain}{iframe_path}"
        else:
            ifurl = f"https://{base_domain}/{iframe_path}"
        
        iframe_content = await self.mlooc_curl_get(ifurl)
        
        # 提取参数
        segment_match = re.findall(r"wp_sign = '(.*?)'", iframe_content)
        signs_match = re.findall(r"ajaxdata = '(.*?)'", iframe_content)
        ajaxm_match = re.findall(r"ajaxm\.php\?file=(\d+)", iframe_content)
        
        if not segment_match or not signs_match or not ajaxm_match:
            raise Exception("解析页面参数失败")
        
        post_data = {
            "action": "downprocess",
            "websignkey": signs_match[0],
            "signs": signs_match[0],
            "sign": segment_match[0],
            "websign": '',
            "kd": 1,
            "ves": 1
        }
        
        # 使用原始域名构建ajax URL
         ajax_url = f"https://{base_domain}/ajaxm.php?file={ajaxm_match[1] if len(ajaxm_match) > 1 else ajaxm_match[0]}"
        response = await self.mlooc_curl_post(post_data, ajax_url, ifurl)
        
        return response
    
    async def _get_final_download_url(self, download_info):
        """获取最终下载链接"""
        # 解析返回的JSON
        try:
            result = json.loads(download_info)
        except json.JSONDecodeError:
            raise Exception("解析响应失败")
        
        if result.get('zt') != 1:
            raise Exception(result.get('inf', '解析失败'))
        
        # 拼接下载链接
        down_url1 = f"{result['dom']}/file/{result['url']}"
        
        # 解析最终直链地址
        down_url2 = await self.mlooc_curl_head(
            down_url1,
            "https://developer.lanzoug.com",
            self.default_user_agent
        )
        
        # 确定最终下载链接
        if "http" not in down_url2:
            down_url = down_url1
        else:
            down_url = down_url2
        
        # 修复正则表达式，移除可能泄露服务器IP的pid参数
        down_url = re.sub(r'pid=.*?&', '', down_url)
        
        return down_url
    
    async def mlooc_curl_get(self, url: str, user_agent: str = None, retry_count: int = 3):
        """异步GET请求，支持重试"""
        if user_agent is None:
            user_agent = self.default_user_agent
        headers = {
            'User-Agent': user_agent,
            'X-FORWARDED-FOR': self.rand_ip(),
            'CLIENT-IP': self.rand_ip(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        return response.text
                    else:
                        raise Exception(f"HTTP {response.status_code}: {response.reason_phrase}")
            except httpx.TimeoutException:
                if attempt == retry_count - 1:
                    raise Exception("请求超时，请检查网络连接")
                logger.warning(f"请求超时，正在重试 ({attempt + 1}/{retry_count})")
            except httpx.ConnectError:
                if attempt == retry_count - 1:
                    raise Exception("连接失败，请检查网络或链接是否正确")
                logger.warning(f"连接失败，正在重试 ({attempt + 1}/{retry_count})")
            except Exception as e:
                if attempt == retry_count - 1:
                    raise Exception(f"请求失败: {str(e)}")
                logger.warning(f"请求失败，正在重试 ({attempt + 1}/{retry_count}): {str(e)}")

    async def mlooc_curl_post(self, post_data: dict, url: str, referer: str = "", user_agent: str = None):
        """异步POST请求"""
        if user_agent is None:
            user_agent = self.default_user_agent
        headers = {
            'User-Agent': user_agent,
            'X-FORWARDED-FOR': self.rand_ip(),
            'CLIENT-IP': self.rand_ip(),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        if referer:
            headers['Referer'] = referer
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(url, data=post_data, headers=headers)
                return response.text
            except Exception as e:
                raise Exception(f"POST请求失败: {str(e)}")

    async def mlooc_curl_head(self, url: str, referer: str, user_agent: str):
        """获取重定向URL"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': user_agent,
            'Referer': referer
        }
        
        async with httpx.AsyncClient(follow_redirects=False, timeout=10) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code in [301, 302, 303, 307, 308]:
                    return response.headers.get('Location', '')
                return ''
            except Exception:
                return ''

    async def parse_lanzou_url(self, url: str, pwd: Optional[str] = None):
        """解析蓝奏云链接"""
        if not url:
            raise Exception("请输入URL")
        
        # 标准化链接格式
        original_url = url
        if '.com/' in url and 'lanzou' not in url:
            path_part = url.split('.com/')[1]
            url = 'https://www.lanzoup.com/' + path_part
        
        # 获取页面内容
        soft_info = await self.mlooc_curl_get(url)
        
        # 检查文件是否失效
        if "文件取消分享了" in soft_info:
            raise Exception("文件取消分享了")
        
        # 提取文件信息
        file_info = self._extract_file_info(soft_info)
        
        # 处理密码保护和公开链接
        if "function down_p(){" in soft_info:
            download_info = await self._handle_password_protected_link(soft_info, url, pwd, file_info)
        else:
            download_info = await self._handle_public_link(soft_info, url, file_info)
        
        # 获取最终下载链接
        final_url = await self._get_final_download_url(download_info)
        
        return {
            "name": file_info.get('name', '未知文件'),
            "filesize": file_info.get('size', '未知大小'),
            "downUrl": final_url
        }

    @filter.command("lanzou")
    async def parse_lanzou_command(self, event: AstrMessageEvent):
        """解析蓝奏云链接指令"""
        message_str = event.message_str.strip()
        
        # 解析命令参数
        parts = message_str.split()
        if len(parts) < 2:
            yield event.plain_result("使用方法：/lanzou <蓝奏云链接> [密码]\n例如：/lanzou https://www.lanzoup.com/ixxxxxx\n或：/lanzou https://www.lanzoup.com/ixxxxxx 密码")
            return
        
        url = parts[1]
        pwd = parts[2] if len(parts) > 2 else None
        
        try:
            logger.info(f"开始解析蓝奏云链接: {url}")
            result = await self.parse_lanzou_url(url, pwd)
            
            response = f"✅ 解析成功！\n\n📁 文件名：{result['name']}\n📊 文件大小：{result['filesize']}\n🔗 下载链接：{result['downUrl']}"
            yield event.plain_result(response)
            
        except Exception as e:
            logger.error(f"解析蓝奏云链接失败: {str(e)}")
            yield event.plain_result(f"❌ 解析失败：{str(e)}")

    # 注意：AstrBot目前不支持keyword过滤器，只支持command过滤器
    # 如需自动检测功能，可以考虑使用其他方式实现

    async def terminate(self):
        """插件销毁方法"""
        logger.info("蓝奏云解析插件已卸载")
