Initial corsicaautodeploy

- [0.安装准备](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-0.安装准备)
- [1.源码获取](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-1.源码获取)
- [2.安装与运行](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-2.安装与运行)
  - [2.1 运行前注意事项](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-2.1运行前注意事项)
    - [2.1.1 首先确定自己要部署的环境](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-2.1.1首先确定自己要部署的环境)
    - [2.1.2 接着确定要部署的环境的版本文件](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-2.1.2接着确定要部署的环境的版本文件)
      - [场景1 部署最新版本](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-场景1部署最新版本)
      - [场景2 部署指定URL的版本文件](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-场景2部署指定URL的版本文件)
      - [场景3 部署指定日期的版本文件](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-场景3部署指定日期的版本文件)
  - [2.2 运行教程小结](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-2.2运行教程小结)
- [3. 目录结构](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-3.目录结构)
- [4. 配置信息介绍](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-4.配置信息介绍)
- [5. 命令行选项详解](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.命令行选项详解)
  - [5.1 选择拉起的环境类型(-c、-s、-i)](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.1选择拉起的环境类型(-c、-s、-i))
  - [5.2 选择拉取的版本文件(-u、-d)](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.2选择拉取的版本文件(-u、-d))
  - [5.3 指定配置文件的路径(–config)](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.3指定配置文件的路径(–config))
  - [5.4 功能选项(–reboot，–release，--deploy-all)](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.4功能选项(–reboot，–release，--deploy-all))
  - [5.5 高阶选项(--search-url, --url-pattern)](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.5高阶选项(--search-url,--url-pattern))
  - [5.6 隐藏选项（-r或--recovery）](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-5.6隐藏选项（-r或--recovery）)
- [6. 部署B720版本示例](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-6.部署B720版本示例)
  - [6.1 获取版本链接：](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-6.1获取版本链接：)
  - [6.2 部署：](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-6.2部署：)
    - [方法一：一次性部署全部](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-方法一：一次性部署全部)
    - [方法二：逐个部署](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-方法二：逐个部署)
      - [部署SCP：](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-部署SCP：)
      - [部署IMU：](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-部署IMU：)
      - [部署业务：](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-部署业务：)
- [7 注意事项](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-7注意事项)
  - [7.1 searching url一定不能直接从浏览器的地址栏中复制](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-7.1searchingurl一定不能直接从浏览器的地址栏中复制)
- [8.安装遇到问题](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-8.安装遇到问题)
  - [8.1 执行部署命令时报“ModuleNotFoundError: No module named 'bs4'”](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-8.1执行部署命令时报“ModuleNotFoundError:Nomodulenamed'bs4'”)
  - [8.2 执行部署命令时报“ModuleNotFoundError: No module named 'paramiko'”](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-8.2执行部署命令时报“ModuleNotFoundError:Nomodulenamed'paramiko'”)
  - [8.3执行部署命令时报错“AttributeError: module 'lib' has no attribute 'X509_V_FLAG_NOTIFY_POLICY'”](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-8.3执行部署命令时报错“AttributeError:module'lib'hasnoattribute'X509_V_FLAG_NOTIFY_POLICY'”)
  - [8.4执行部署命令时报错](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-8.4执行部署命令时报错)
  - [8.5 执行部署命令时报错”No matching distribution found for ipmitool“](http://space.jaguarmicro.com/pages/viewpage.action?pageId=96971600#id-030302corsica自动化部署工具文档-8.5执行部署命令时报错”Nomatchingdistributionfoundforipmitool“)



# 0.安装准备

```
pip install paramiko
```

# 1.源码获取

代码仓库地址：[ssh://git@bb.jaguarmicro.com:7999/jsitest/corsicaautodeploy.git](ssh://git@bb.jaguarmicro.com:7999/jsitest/corsicaautodeploy.git)

```
git clone ssh://git@bb.jaguarmicro.com:7999/jsitest/corsicaautodeploy.git       // 需在vdi内操作
cd corsicaAutoDeploy
```

# 2.安装与运行

```
// 本工具无需安装，运行时需切换当前工作目录至run.py所在的目录
cd /path/to/project
```

### 2.1 运行前注意事项

#### 2.1.1 首先确定自己要部署的环境

如果需要拉起业务版本，那么就使用-c选项，如果是更新imu版本，那么就使用-i选项，如果是SCP，那么就使用-s选项。

```
python run.py -c    // 拉起业务版本
python run.py -i    // 更新IMU固件
python run.py -s    // 更新SCP固件
python run.py --reboot // 重启N2
python run.py -c --release  // 使用release版本来拉起业务，注意这里只能是-c，因为-i和-s都没有release的业务版本
 
python run.py -i -s     // 错误示范，-i,-c,-s是互斥的，每次只能部署一个类型的版本。
```

#### 2.1.2 接着确定要部署的环境的版本文件

##### 场景1 部署最新版本

```
python run.py -c    // 默认拉取最新的版本文件进行部署
python run.py -i   
python run.py -s   
```

##### 场景2 部署指定URL的版本文件

```
python run.py -c -u https://url/to/version_file.tar.gz      // -u 后面接着版本文件的下载地址即可
python run.py -i -u https://url/to/version_file.img
python run.py -s -u https://url/to/version_file.img
```

##### 场景3 部署指定日期的版本文件

```
python run.py -c -d 202401121043  // -d 后面指定版本文件的构建日期
python run.py -i -d 202401121043
python run.py -s -d 202401121043
```

![image-20240228095230977](http://wenxuanqiu.oss-cn-nanjing.aliyuncs.com/img/20240228095232.png)

这里需注意，-d 后面指定的日期必须在搜索的页面上可以找得到，搜索页面的网址在config文件夹下的env.config中配置。

### 2.2 运行教程小结

```
// 更新业务版本
python run.py -c    //  拉起业务版本，而且拉取的版本是每日构建中最新的一版
python run.py -c -u https://url/to/version_file.tar.gz      // 拉起业务版本，而且指定了拉取的版本文件的下载地址
pyrhon run.py -c -d 202401121043    // 拉起业务版本，而且指定了拉取的版本文件的构建日期
 
// 更新IMU固件版本
pyrhon run.py -i    // 更新IMU固件版本，而且拉取的固件版本是每日构建中的最新一版
python run.py -i -u https://url/to/version_file.img     // 更新IMU固件版本，而且指定了拉取的版本文件的下载地址
pyrhon run.py -i -d 202401121043    // 更新IMU固件版本，而且指定了拉取的版本文件的构建日期
 
// 更新SCP固件版本
pyrhon run.py -s    // 更新SCP固件版本，而且拉取的固件版本是每日构建中的最新一版
python run.py -s -u https://url/to/version_file.img     // 更新SCP固件版本，而且指定了拉取的版本文件的下载地址
pyrhon run.py -s -d 202401121043    // 更新SCP固件版本，而且指定了拉取的版本文件的构建日期
 
// 三种场景的版本都需更新
python run.py --deploy-all      // 使用最新的每日构建版本，更新imu、scp和业务版本
python run.py --deploy-all --cloud-url https://url/to/version_file.tar.gz --scp-url https://url/to/version_file.img  --imu-url https://url/to/version_file.img          // 部署三种场景，并且使用指定的版本文件进行部署
```

# 3. 目录结构

```
├── cloudsupported
│   ├── cloud_deploy.py           // 存放着云部署的代码
│   ├── __init__.py
├── common
├── config
│   ├── bm_config.json        // 拉起业务版本时，这个文件会拷贝到N2，修改原来的配置
│   └── env.conf              // 配置环境信息，例如N2的IP，用户名和密码等，还可以配置读取业务版本的路径
├── firmware
│   ├── imu
│   │   ├── imu_deploy.py       // 存放着IMU部署的代码
│   └── scp
│       └── scp_deploy.py         // SCP部署的代码
├── kernel
├── rdma
├── run.py          // 程序的入口文件
└── version
```

# 4. 配置信息介绍

```
[N2]        // N2的登录信息配置
hostname = 10.21.186.168
port = 22
username = root
password = root
 
[host]      // host的登录信息配置
hostname = 10.21.187.91
port = 22
username = root
password = jaguar1
 
[N2BMC]     // N2BMC的登录信息
hostname = 10.21.186.68
port = 22
username = root
password = 0penBmc
 
[hostBMC]   // hostBMC的登录信息
hostname = 10.21.187.92
port = 22
username = admin
password = admin
 
[profile]   // JFrog的登录信息配置
JFrog_username = barney.zhi
JFrog_password = Zqc@hhu2023
 
[cloudSupportVersionFileConfig]     // 配置业务版本的下载地址配置
searching_url = https://jfrog1.jaguarmicro.com:443/artifactory/corsica-sw-generic-local/snapshot/full-version/corsica_dpu_dev/anolis/      
filePattern = https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/snapshot/full-version/corsica_dpu_dev/anolis/@{download_date}/@{download_date}_jmnd.tar.gz
 
// searching_url主要用于获取每日构建的最新日期，接着，这个日期会被嵌入到对应的filePattern中，可以看到filePattern中有@{download_date}，运行时，这个@{download_date}会被替换成searching_url中找到的最新日期（如果使用了-d选项指定日期，那么这个日期会直接嵌入到filePattern中）
 
[imuVersionFileConfig]
searching_url = https://jfrog1.jaguarmicro.com:443/artifactory/corsica-sw-generic-local/snapshot/imu-version/corsica_dpu_dev/ubuntu/
filePattern = https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/snapshot/imu-version/corsica_dpu_dev/ubuntu/@{download_date}/crb_5_imu_flash_@{download_date}.img
 
[scpVersionFileConfig]
searching_url = https://jfrog1.jaguarmicro.com:443/artifactory/corsica-soc-generic-local/snapshot/daily-build/
filePattern = https://jfrog1.jaguarmicro.com/artifactory/corsica-soc-generic-local/snapshot/daily-build/@{download_date}/package/crb/scp_flash_crb_5_n2_2.0g_cmn_1.65g.img
 
[log_output_path]       // log日志文件是更新IMU和SCP时产生的，这个日志文件主要是用于获取fireware.sh的实时进度
imu_log_filepath = '/tmp/imu_deploy.log'
scp_log_filepath = '/tmp/scp_deploy.log'
```

**xxxVersionFileConfig下的searching_url主要用于获取每日构建的最新日期，接着，这个日期会被嵌入到对应的filePattern中，可以看到filePattern中有${download_date}，运行时，这个${download_date}会被替换成searching_url中找到的最新日期（如果使用了-d选项指定日期，那么-d指定的日期会直接嵌入到filePattern中）**

# 5. 命令行选项详解

## 5.1 选择拉起的环境类型(-c、-s、-i)

-c表示拉起业务版本, -s表示更新scp固件，-i表示更新imu固件

```
python run.py -c    // 拉起业务版本
python run.py -i    // 更新IMU固件
python run.py -s    // 更新SCP固件
```

## 5.2 选择拉取的版本文件(-u、-d)

-u用于指定下载的版本文件url，-d指定下载版本文件的日期（–date)

```
python run.py -c -u https://url/to/version_file.tar.gz      // -u 后面接着版本文件的下载地址即可
python run.py -c -d 202401121043  // -d 后面指定版本文件的构建日期
```

## 5.3 指定配置文件的路径(–config)

```
python run.py -c --config "/path/to/myconfig.conf"      // 指定了myconfig.conf作为配置文件，默认使用./config/env.conf（确保你的myconfig.conf文件中具有env.conf中的所有配置项！）
```

## 5.4 功能选项(–reboot，–release，--deploy-all)

```
python run.py --reboot // 重启N2
python run.py -c --release  // 使用release版本来拉起业务，注意这里只能是-c，因为-i和-s都没有release的业务版本
python run.py --deploy-all      // 使用最新的每日构建版本，更新imu、scp和业务版本
```

## 5.5 高阶选项(--search-url, --url-pattern)

```
// 示例用法
// --search-url选项可以在命令行中直接修改env.config中的对应的xxxVersionFileConfig下的searching_url的值
// --url-pattern选项可以在命令行中直接修改env.config中的对应的xxxVersionFileConfig下的url_pattern的值
// --search-url指定用于搜索版本文件的最新构建日期的网页地址，在程序中对应于下载的index.html的内容
// --url-pattern选项用于指定版本文件的模式，其中通过自定义的语法@{download_date}，可以将在index.html中寻找到的最新构建日期嵌入到网址中的@{download_date}部分
python run.py -c --search-url https://jfrog1.jaguarmicro.com:443/artifactory/corsica-sw-generic-local/snapshot/full-version/corsica_dpu_dev/anolis/ --url-pattern https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/snapshot/full-version/corsica_dpu_dev/anolis/@{download_date}/@{download_date}_jmnd.tar.gz
```

## 5.6 隐藏选项（-r或--recovery）

```
python run.py -r    //  只有产品测试部的44个用例的部署时会用到这个选项，这个选项主要是用于将N2上/usr/share/jmnd/single/auto/config/bm_config.json.bak 覆盖掉当前的bm_config.json// 上面的这行就相当于是到N2上执行了下面的一行命令：cd /usr/share/jmnd/single/auto/config && cp -f bm_config.json.bak bm_config.json 
```

bm_config.json.bak是拉起业务时自动创建的，这个文件是原始的业务版本文件中自带的配置文件，而拉起我们组内的CRB环境时用不到这个配置文件，相反，我们会提供一个我们自己的bm_config.json文件，为了保留这个原始的配置文件，我拉起业务时会拷贝一份，并且添加后缀名.bak，来表示这是原始配置文件的一个备份。

# 6. 部署B720版本示例

## 6.1 获取版本链接：

scp：https://jfrog1.jaguarmicro.com/ui/native/corsica-soc-generic-local/release/release_v2.5.1_bugfix0110/package/crb/scp_flash_crb_5_n2_2.0g_cmn_1.65g.img
IMU：https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/release/imu-version/ubuntu/corsica_1.0.0.B720/crb_5_imu_flash_202401101758.img
业务：[https://jfrog1.jaguarmicro.com:443/artifactory/corsica-sw-generic-local/release/full-version/anolis/corsica_1.0.0.B720/corsica_1.0.0.B720_jmnd.tar.gz](https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/release/full-version/anolis/corsica_1.0.0.B720/corsica_1.0.0.B720_jmnd.tar.gz)

## 6.2 部署：

### 方法一：一次性部署全部

```
python run.py --deploy-all --cloud-url https://jfrog1.jaguarmicro.com:443/artifactory/corsica-sw-generic-local/release/full-version/anolis/corsica_1.0.0.B720/corsica_1.0.0.B720_jmnd.tar.gz --scp-url https://jfrog1.jaguarmicro.com/ui/native/corsica-soc-generic-local/release/release_v2.5.1_bugfix0110/package/crb/scp_flash_crb_5_n2_2.0g_cmn_1.65g.img  --imu-url https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/release/imu-version/ubuntu/corsica_1.0.0.B720/crb_5_imu_flash_202401101758.img
```

### 方法二：逐个部署

#### 部署SCP：

```
python run.py -s -u https://jfrog1.jaguarmicro.com/ui/native/corsica-soc-generic-local/release/release_v2.5.1_bugfix0110/package/crb/scp_flash_crb_5_n2_2.0g_cmn_1.65g.img
```

#### 部署IMU：

```
python run.py -i -u https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/release/imu-version/ubuntu/corsica_1.0.0.B720/crb_5_imu_flash_202401101758.img
```

#### 部署业务：

```
python run.py -c -u https://jfrog1.jaguarmicro.com:443/artifactory/corsica-sw-generic-local/release/full-version/anolis/corsica_1.0.0.B720/corsica_1.0.0.B720_jmnd.tar.gz
```



# 7 注意事项

## 7.1 searching url一定不能直接从浏览器的地址栏中复制

![image-20240228095254485](http://wenxuanqiu.oss-cn-nanjing.aliyuncs.com/img/20240228095255.png)

原始的网址是：https://jfrog1.jaguarmicro.com/artifactory/corsica-sw-generic-local/snapshot/full-version/corsica_dpu_dev/anolis/

如果在浏览器的地址栏中访问上面的这个网址，会被重定向到：https://jfrog1.jaguarmicro.com/ui/native/corsica-sw-generic-local/snapshot/full-version/corsica_dpu_dev/anolis/

![image-20240228095303644](http://wenxuanqiu.oss-cn-nanjing.aliyuncs.com/img/20240228095304.png)

**注意对于重定向后的网址，程序是无法获取其中的网页内容的，因此如果程序想要通过requests库或者是wget的方式去获取版本文件的最新日期的话，请使用包含artfactory的网址（即原始网址），而不要使用浏览器重定向后的包含ui/native的网址。**

# 8.安装遇到问题

## 8.1 执行部署命令时报“ModuleNotFoundError: No module named 'bs4'”

![image-20240228095318437](http://wenxuanqiu.oss-cn-nanjing.aliyuncs.com/img/20240228095319.png)

执行

```
apt-get install python3-bs4
```

## 8.2 执行部署命令时报“ModuleNotFoundError: No module named 'paramiko'”

执行

```
pip3 install paramiko
```

## 8.3执行部署命令时报错“AttributeError: module 'lib' has no attribute 'X509_V_FLAG_NOTIFY_POLICY'”

执行

```
sudo rm -rf /usr/lib/python3/dist-packages/OpenSSL
sudo pip3 install pyopenssl
sudo pip3 install pyopenssl --upgrade
```

## 8.4执行部署命令时报错

执行

```
apt-get install sshpass
```

## 8.5 执行部署命令时报错”No matching distribution found for ipmitool“

执行

```
apt-get install ipmitool
```
