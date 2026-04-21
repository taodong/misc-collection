# Email Sender

Email sender is a python tool to connect a smtp server to send out emails based on a give template.

The connection method is ssl and the sample connection config is like the following

```
swaks --server {server_url} \
      --auth-user {auth_user} \
      --auth-password {auth_password} \
      --tls \
      --to test@example.com \
```

## Configuration
The tool should look for `config.json` in local directory before sending the email. Sample json file is like
```
{
  "server_url": "localhost",
  "server_port": 9587,
  "auth_user": "myuser",
  "auth_password": "mypassword",
  "sender_email": "noreply@yourdomain.com"
}
```

All fields are required.

## Template
All email templates will be stored under `templates` folder using `.txt` format. The template name is the file name case insensitive.

For example, `hello` template matches the file `templates/hello.txt`

The content (`template variables`) needs to be replaced in the template is wrapped with `{{}}`, for example `{{name}}` should be replaced by a user provided value before sending

## Flow
The working flow of the tool is like:
1. Start tool in console
2. Tool check the configuration
3. Tool prompt for input and confirm recipient email address
4. Tool prompt for input of the subject line
5. Tool prompt for template name
6. Tool goes through the template and prompt user to input all the template variables
7. Tool present a review screen listed finalized email
8. Tool connect to the smtp server and send out the email
9. Tool output success message and terminate itself

## Error Handling
For any missing configuration or operation failure, output erorr messange and exit the tool

## Terminate
Tool can be terminated anytime by `ctrl-c`

## Test
Add some tests to cover the flow
