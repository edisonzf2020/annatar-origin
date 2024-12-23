```markdown
# Real-Debrid API 文档

## 实现细节

*   方法按命名空间分组（例如“unrestrict”，“user”）。
*   支持的 HTTP 动词有 GET、POST、PUT 和 DELETE。如果您的客户端不支持所有 HTTP 动词，您可以使用 X-HTTP-Verb HTTP 标头覆盖该动词。
*   除非在方法的文档中另有说明，否则所有成功的 API 调用都返回带有 JSON 对象的 HTTP 代码 200。
*   错误返回 HTTP 代码 4XX 或 5XX，一个带有属性“error”（错误消息）和“error_code”（可选，一个整数）的 JSON 对象。
*   传递给 API 和从 API 传递的每个字符串都需要进行 UTF-8 编码。为了最大兼容性，请在 UTF-8 编码之前规范化为 Unicode 规范化形式 C（NFC）。
*   API 发送 ETag 标头并支持 If-None-Match 标头。
*   日期根据 Javascript 方法 date.toJSON 进行格式化。
*   除非另有说明，否则所有 API 方法都需要身份验证。
*   API 限制为每分钟 250 个请求，所有被拒绝的请求都将返回 HTTP 429 错误，并将计入限制（暴力破解将使您被阻止的时间不确定）

## API 方法

Rest API 的基本 URL 是：

```
https://api.real-debrid.com/rest/1.0/
```

| 方法                               | 描述                                         |
| :--------------------------------- | :------------------------------------------- |
| `GET /disable_access_token`         | 禁用当前访问令牌                               |
| `GET /time`                        | 获取服务器时间                                 |
| `GET /time/iso`                     | 以 ISO 格式获取服务器时间                       |
| `/user`                             |                                              |
| `GET /user`                        | 获取当前用户信息                               |
| `/unrestrict`                       |                                              |
| `POST /unrestrict/check`           | 检查链接                                     |
| `POST /unrestrict/link`            | 解除链接限制                                 |
| `POST /unrestrict/folder`          | 解除文件夹链接限制                           |
| `PUT /unrestrict/containerFile`    | 解密容器文件                                 |
| `POST /unrestrict/containerLink`   | 从链接解密容器文件                           |
| `/traffic`                          |                                              |
| `GET /traffic`                     | 受限主机商的流量信息                           |
| `GET /traffic/details`             | 已使用主机商的流量详细信息                     |
| `/streaming`                        |                                              |
| `GET /streaming/transcode/{id}`    | 获取给定文件的转码链接                         |
| `GET /streaming/mediaInfos/{id}`   | 获取给定文件的媒体信息                         |
| `/downloads`                        |                                              |
| `GET /downloads`                    | 获取用户下载列表                             |
| `DELETE /downloads/delete/{id}`    | 从下载列表中删除链接                           |
| `/torrents`                         |                                              |
| `GET /torrents`                     | 获取用户种子列表                             |
| `GET /torrents/info/{id}`           | 获取种子的信息                               |
| `GET /torrents/activeCount`        | 获取当前活动的种子数量                         |
| `GET /torrents/availableHosts`     | 获取可用的主机                               |
| `PUT /torrents/addTorrent`         | 添加种子文件                                 |
| `POST /torrents/addMagnet`         | 添加磁力链接                                 |
| `POST /torrents/selectFiles/{id}`   | 选择种子的文件                               |
| `DELETE /torrents/delete/{id}`     | 从种子列表中删除种子                           |
| `/hosts`                            |                                              |
| `GET /hosts`                        | 获取支持的主机                               |
| `GET /hosts/status`                 | 获取主机商的状态                             |
| `GET /hosts/regex`                  | 获取所有支持的正则表达式。                   |
| `GET /hosts/regexFolder`            | 获取文件夹链接的所有支持的正则表达式。         |
| `GET /hosts/domains`                | 获取所有支持的域名。                         |
| `/settings`                         |                                              |
| `GET /settings`                     | 获取当前用户设置                             |
| `POST /settings/update`            | 更新用户设置                                 |
| `POST /settings/convertPoints`      | 转换积分                                     |
| `POST /settings/changePassword`     | 发送验证电子邮件以更改密码                     |
| `PUT /settings/avatarFile`         | 上传头像图片                                 |
| `DELETE /settings/avatarDelete`     | 重置用户头像                                 |
| `/support`                          |  *未提供*                                       |

## 示例调用

以下是一些使用 cURL 的示例调用：

获取用户信息：

```bash
curl -H "Authorization: Bearer YOUR_API_TOKEN" "https://api.real-debrid.com/rest/1.0/user"
```

## 身份验证

需要身份验证的调用需要一个带有令牌的 HTTP 标头 `Authorization`，使用以下格式：

```
Authorization: Bearer your_api_token
```

如果您无法发送 `Authorization` HTTP 标头，您还可以在 REST API URL 中将令牌作为参数发送，该参数称为 `auth_token`：

```
/rest/1.0/method?auth_token=your_api_token
```

此令牌可以是您的私有 API 令牌，也可以是使用 OAuth2 的三方身份验证获得的令牌。

**警告：** 切勿将您的私有 API 令牌用于公共应用程序，它不安全并且可以访问所有方法。

## 应用程序的身份验证

首先，您必须在您的[控制面板](https://real-debrid.com/account)中创建一个应用程序。

创建应用程序后，您将获得一个 `client_id` 和 `client_secret`，您将在身份验证过程中使用它们。

### 开源应用程序

如果您不需要自定义范围或名称，您可以在开源应用程序上使用此客户端 ID：

```
X245A4XAIBGVM
```

此应用程序允许在以下范围内使用：`unrestrict`，`torrents`，`downloads`，`user`

由于使用它的设计不良的应用程序，此客户端 ID 的限制可能比服务限制更严格。

### 您应该使用哪种身份验证流程？

*   如果您的应用程序是**网站**：三方 OAuth2。
*   如果您的应用程序是**移动应用程序**：OAuth2 for devices。
*   如果您的应用程序是**开源应用程序或脚本**：OAuth2 for opensource apps。

OAuth2 API 的基本 URL 是：

```
https://api.real-debrid.com/oauth/v2/
```

### 网站或客户端应用程序的工作流程

此身份验证过程使用三方 OAuth2。

在此过程中使用以下 URL：

*   授权端点：`/auth`
*   令牌端点：`/token`

**注意：** 如果您的应用程序不是网站，则必须让用户在 Web 视图中执行这些步骤（例如 iOS 上的 UIWebView，Android 上的 WebView…）。

**完整工作流程**

1. 您的应用程序将用户重定向到 Online.net 的授权端点，并带有以下查询字符串参数：
    *   `client_id`：您的应用程序的 `client_id`
    *   `redirect_uri`：您的应用程序的重定向 URL 之一（必须进行 url 编码）
    *   `response_type`：使用值“code”
    *   `state`：将返回到您的应用程序的任意字符串，以帮助您检查 CSRF

    授权的示例 URL：

    ```
    https://api.real-debrid.com/oauth/v2/auth?client_id=ABCDEFGHIJKLM&redirect_uri=https%3A%2F%2Fexample.com&response_type=code&state=iloverd
    ```

2. 用户选择授权您的应用程序。

3. 用户被重定向到您使用参数 `redirect_uri` 指定的 URL，并带有以下查询字符串参数：
    *   `code`：您将用来获取令牌的代码
    *   `state`：您之前发送的相同值

4. 使用 `code` 的值，您的应用程序直接向令牌端点发出 POST 请求（不在用户的浏览器中），并带有以下参数：
    *   `client_id`
    *   `client_secret`
    *   `code`：您之前收到的值
    *   `redirect_uri`：您的应用程序的重定向 URL 之一
    *   `grant_type`：使用值“authorization_code”

    获取访问令牌的示例 cURL 调用：

    ```bash
    curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "client_id=ABCDEFGHIJKLM&client_secret=abcdefghsecret0123456789&code=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&redirect_uri=https://your-app.tld/realdebrid_api&grant_type=authorization_code"
    ```

5. 如果一切正确，则将访问令牌作为具有以下属性的 JSON 对象返回：
    *   `access_token`
    *   `expires_in`：令牌有效期，以秒为单位
    *   `token_type`：“Bearer”
    *   `refresh_token`：仅当用户撤销您的应用程序权限时才会过期的令牌

6. 您的应用程序存储访问令牌并在用户后续访问时使用它。

7. 您的应用程序还必须存储刷新令牌，该刷新令牌将在访问令牌的有效期到期后用于获取新的访问令牌。

### 移动应用程序的工作流程

此身份验证过程使用 OAuth2 的变体，专为移动设备量身定制。

在此过程中使用以下 URL：

*   设备端点：`/device/code`
*   令牌端点：`/token`

**注意：** 如果您想从移动应用程序执行所有这些步骤，您可能需要让用户在 Web 视图中执行某些步骤（例如 iOS 上的 UIWebView，Android 上的 WebView…）。

**完整工作流程**

1. 您的应用程序直接向设备端点发出请求，并带有查询字符串参数 `client_id`，并获取一个带有身份验证数据的 JSON 对象，该对象将在该过程的其余部分中使用。

    获取身份验证数据的示例 URL：

    ```
    https://api.real-debrid.com/oauth/v2/device/code?client_id=ABCDEFGHIJKLM
    ```

    示例身份验证数据：

    ```json
    {
        "device_code": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "user_code": "ABCDEF0123456",
        "interval": 5,
        "expires_in": 1800,
        "verification_url": "https:\/\/real-debrid.com\/device"
    }
    ```

2. 您的应用程序要求用户转到验证端点（由 `verification_url` 提供）并键入 `user_code` 提供的代码。

3. 使用 `device_code` 的值，每 5 秒，您的应用程序开始直接向令牌端点发出 POST 请求，并带有以下参数：
    *   `client_id`
    *   `client_secret`
    *   `code`：`device_code` 的值
    *   `grant_type`：使用值“http://oauth.net/grant_type/device/1.0”"

    获取访问令牌的示例 cURL 调用：

    ```bash
    curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "client_id=ABCDEFGHIJKLM&client_secret=abcdefghsecret0123456789&code=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&grant_type=http://oauth.net/grant_type/device/1.0"
    ```

4. 在用户输入代码并授权应用程序之前，您的应用程序将收到一条错误消息。

5. 用户输入代码，然后登录（如果他们尚未登录）。

6. 用户选择授权您的应用程序，然后可以关闭浏览器窗口。

7. 您的应用程序对令牌端点的调用现在将访问令牌作为具有以下属性的 JSON 对象返回：
    *   `access_token`
    *   `expires_in`：令牌有效期，以秒为单位
    *   `token_type`：“Bearer”
    *   `refresh_token`：仅当用户撤销您的应用程序权限时才会过期的令牌

8. 您的应用程序存储访问令牌并在用户后续访问时使用它。

9. 您的应用程序还必须存储刷新令牌，该刷新令牌将在访问令牌的有效期到期后用于获取新的访问令牌。

### 开源应用程序的工作流程

此身份验证过程类似于 OAuth2 for mobile devices，不同之处在于开源应用程序或脚本无法附带 `client_secret`（因为它应该是保密的）。

此处的原则是获取一组绑定到用户的新 `client_id` 和 `client_secret`。您可以通过使用 OAuth2 for mobile devices 重复使用这些凭据。

**警告：** 您不应重新分发凭据。与其他帐户一起使用将显示获取凭据的用户的 UID。例如，它将显示“最精彩的应用程序（UID：000）”，而不是显示“最精彩的应用程序”。

在此过程中使用以下 URL：

*   设备端点：`/device/code`
*   凭据端点：`/device/credentials`
*   令牌端点：`/token`

**完整工作流程**

1. 您的应用程序直接向设备端点发出请求，并带有查询字符串参数 `client_id` 和 `new_credentials=yes`，并获取一个带有身份验证数据的 JSON 对象，该对象将在该过程的其余部分中使用。

    获取身份验证数据的示例 URL：

    ```
    https://api.real-debrid.com/oauth/v2/device/code?client_id=ABCDEFGHIJKLM&new_credentials=yes
    ```

    示例身份验证数据：

    ```json
    {
        "device_code": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "user_code": "ABCDEF0123456",
        "interval": 5,
        "expires_in": 1800,
        "verification_url": "https:\/\/real-debrid.com\/device"
    }
    ```

2. 您的应用程序要求用户转到验证端点（由 `verification_url` 提供）并键入 `user_code` 提供的代码。

3. 使用 `device_code` 的值，每 5 秒，您的应用程序开始直接向凭据端点发出请求，并带有以下查询字符串参数：
    *   `client_id`
    *   `code`：`device_code` 的值

4. 在用户输入代码并授权应用程序之前，您的应用程序将收到一条错误消息。

5. 用户输入代码，然后登录（如果他们尚未登录）。

6. 用户选择授权您的应用程序，然后可以关闭浏览器窗口。

7. 您的应用程序对凭据端点的调用现在返回一个具有以下属性的 JSON 对象：
    *   `client_id`：绑定到用户的新 `client_id`
    *   `client_secret`

8. 您的应用程序存储这些值，并将在以后的请求中使用它们。

9. 使用 `device_code` 的值，您的应用程序直接向令牌端点发出 POST 请求，并带有以下参数：
    *   `client_id`：调用凭据端点提供的值 `client_id`
    *   `client_secret`：调用凭据端点提供的值 `client_secret`
    *   `code`：`device_code` 的值
    *   `grant_type`：使用值“http://oauth.net/grant_type/device/1.0”

    答案将是一个具有以下属性的 JSON 对象：
    *   `access_token`
    *   `expires_in`：令牌有效期，以秒为单位
    *   `token_type`：“Bearer”
    *   `refresh_token`：仅当用户撤销您的应用程序权限时才会过期的令牌

    获取访问令牌的示例 cURL 调用：

    ```bash
    curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "client_id=ABCDEFGHIJKLM&client_secret=abcdefghsecret0123456789&code=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&grant_type=http://oauth.net/grant_type/device/1.0"
    ```

10. 您的应用程序存储访问令牌并在用户后续访问时使用它。

11. 您的应用程序还必须存储刷新令牌，该刷新令牌将在访问令牌的有效期到期后用于获取新的访问令牌。

### 旧版应用的工作流程

**警告：** 此工作流程需要 Webmaster 对您的 `client_id` 进行特殊授权。

在此过程中使用以下 URL：

*   令牌端点：`/token`

**完整工作流程**

1. 您的应用程序直接向令牌端点发出 POST 请求，并带有以下参数：
    *   `client_id`
    *   `username`：用户登录名
    *   `password`：用户密码
    *   `grant_type`：使用值“password”

    **测试双因素流程**

    **仅出于测试目的**，您可以通过发送以下内容强制服务器向您提供双因素错误：

    ```
    force_twofactor: true
    ```

    这将返回双因素验证 URL：

    *   `verification_url`：您应该将用户重定向到的 URL。
    *   `twofactor_code`
    *   `error`：“twofactor_auth_needed”
    *   `error_code`：11

    **如果您使用 WebView / 弹出窗口的工作流程**

    1. 使用 `verification_url` 的值打开一个 WebView / 弹出窗口
    2. 使用 `twofactor_code` 的值，您的应用程序直接向令牌端点发出 POST 请求（不在用户的浏览器中），并带有以下参数：
        *   `client_id`
        *   `code`：您之前收到的值
        *   `grant_type`：使用值“twofactor”

        获取访问令牌的示例 cURL 调用：

        ```bash
        curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "client_id=ABCDEFGHIJKLM&code=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&grant_type=twofactor"
        ```

    在用户在 `verification_url` 上输入正确的安全代码之前，您将获得 403 HTTP 代码。

    **如果您想处理安全代码验证过程的工作流程**

    在您向令牌端点发出请求之前，不会发送 SMS 或电子邮件，并带有以下参数：

    *   `client_id`
    *   `code`：您之前收到的值
    *   `grant_type`：使用值“twofactor”
    *   `send`：true

    成功后，您将获得 204 HTTP 代码，如果达到限制，则将获得 403 HTTP 代码。

    要验证用户提供的安全代码，请向令牌端点发出请求，并带有以下参数：

    *   `client_id`
    *   `code`：您之前收到的值
    *   `grant_type`：使用值“twofactor”
    *   `response`：使用用户输入的值

    出现错误时，您将获得 400 HTTP 代码，如果达到尝试次数，您将获得 403 HTTP 代码。

    成功后，答案将是一个具有以下属性的 JSON 对象：

    *   `access_token`
    *   `expires_in`：令牌有效期，以秒为单位
    *   `token_type`：“Bearer”
    *   `refresh_token`

    **重要提示：** 您不得保存任何登录详细信息，仅将 `refresh_token` 保留为“密码”。

    获取访问令牌的示例 cURL 调用：

    ```bash
    curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "client_id=ABCDEFGHIJKLM&username=abcdefghsecret0123456789&password=abcdefghsecret0123456789&grant_type=password"
    ```

2. 从刷新令牌获取新的访问令牌

    在此过程中使用以下 URL：

    *   令牌端点：`/token`

    **完整工作流程**

    1. 使用您之前保存的 `refresh_token` 的值，您的应用程序直接向令牌端点发出 POST 请求，并带有以下参数：
        *   `client_id`
        *   `client_secret`
        *   `code`：`refresh_token` 的值
        *   `grant_type`：使用值“http://oauth.net/grant_type/device/1.0”

        答案将是一个具有以下属性的 JSON 对象：

        *   `access_token`
        *   `expires_in`：令牌有效期，以秒为单位
        *   `token_type`：“Bearer”
        *   `refresh_token`

        获取访问令牌的示例 cURL 调用：

        ```bash
        curl -X POST "https://api.real-debrid.com/oauth/v2/token" -d "client_id=ABCDEFGHIJKLM&client_secret=abcdefghsecret0123456789&code=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789&grant_type=http://oauth.net/grant_type/device/1.0"
        ```

## 数字错误代码列表


```markdown

In addition to the HTTP error code, errors come with a message (`error` parameter) and a numeric code (`error_code` parameter). The error message is meant to be human-readable, while the numeric codes should be used by your application.

| Code | Description                                         |
| :--- | :-------------------------------------------------- |
| -1   | Internal error                                      |
| 1    | Missing parameter                                   |
| 2    | Bad parameter value                                 |
| 3    | Unknown method                                      |
| 4    | Method not allowed                                  |
| 5    | Slow down                                          |
| 6    | Ressource unreachable                               |
| 7    | Resource not found                                  |
| 8    | Bad token                                           |
| 9    | Permission denied                                   |
| 10   | Two-Factor authentication needed                    |
| 11   | Two-Factor authentication pending                   |
| 12   | Invalid login                                       |
| 13   | Invalid password                                    |
| 14   | Account locked                                      |
| 15   | Account not activated                               |
| 16   | Unsupported hoster                                  |
| 17   | Hoster in maintenance                               |
| 18   | Hoster limit reached                                |
| 19   | Hoster temporarily unavailable                      |
| 20   | Hoster not available for free users                 |
| 21   | Too many active downloads                           |
| 22   | IP Address not allowed                              |
| 23   | Traffic exhausted                                   |
| 24   | File unavailable                                    |
| 25   | Service unavailable                                 |
| 26   | Upload too big                                      |
| 27   | Upload error                                        |
| 28   | File not allowed                                    |
| 29   | Torrent too big                                     |
| 30   | Torrent file invalid                                |
| 31   | Action already done                                |
| 32   | Image resolution error                              |
| 33   | Torrent already active                              |
| 34   | Too many requests                                   |
| 35   | Infringing file                                     |
| 36   | Fair Usage Limit                                    |
| 37   | Disabled endpoint                                   |
```
