# steamlit可视化参考代码 #
*使用方法：*
``` bash
$ streamlit run ./main.py
```
## 相关文件或软件包链接 ##
**→** [豆瓣可视化项目相关程序**持续更新**](https://linyer.lanzoue.com/b0w7qpw7a)

***密码: 2tst***

## 关于添加自定义页面 ##
**由于修改了菜单模式，失去了自动读取页面的能力:**

**自定义菜单的页面放在了 *data/modules.py* 文件里，类型为 *字符串字典***

**请自行添加对应的菜单名和页面py文件属性:**

**例如:**
``` code
{"..": "...", "我的主页": "pages/my_page.py"}
```
## 关于pip库安装 ##
**找到requirements.txt文件目录**

**例如就在本目录下:**
``` bash
$ pip install -r .\requirements.txt --upgrade
```
***upgrade参数是更新，建议加上防止版本过低***