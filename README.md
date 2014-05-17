# TaskPaperManager


TaskPaperManager (TPM) is a little python script to parse and modify a TaskPaper file.
It provides the following features:

* Move done tasks (@done) to a separate archive file
* Check any repeat-tasks (@repeat) and instantiate a new task entry if a repeat-cycle comes up
* send daily status mails for @high, @medium, @duesoon and @overdue tasks
* flag tasks with due-dates as @duesoon or @overdue (helpful for hightlighting with modified TaskPaper Theme)
* Sort the list (primary sort criterium: @prio, secondary: @start)
* Copy tasks with the tag @maybe in a dedicated maybe list and remove from master list

The variable parameters are configured via a separate config file (tpp.cfg):

    [tpm]
    debug: False
    duedelta: days
    dueinterval: 3

    [mail]
    sendmail: True
    smtpserver = <FQDN of your smtp server>
    smtpport = <listening port of your smtp server>
    smtpuser = <your user on the server>
    smtppassword = <your password>
    sourceemail: <sender mail address>
    destworkemail: <receiver mail address; work>
    desthomeemail: <receiver mail address; home>
    encryptmail: True
    gnupghome: <Path to your home>/.gnupg
    targetfingerprint: <Fingerprint of the gpg key of the email receiver>

    [pushover]
    pushover: True
    pushovertoken: <application token>
    pushoveruser: <user string>

*dueinterval:* all tasks will be tagged as @duesoon when today is x days (or whatever you define for *duedelta*) before the duedate (defined in @due(...))

*debug:* When enabling debug mode the script will not modify your tasklist but will print instead debug output. This has no influence on sending email or sending pushover messages.

## Sending email
You can either send email encrypted (gpg) or in plain text. The communication to the server uses SSL/TLS with starttls. Content encryption requires gnupg installed and the python-gnupg module.

## Sending pushover messages
Enter your userstring and application token from pushover into the config file and enable the sending of pushover messages by setting "pushover: True". Pushover messages are limited to a maximum of 512 characters, so the scripts cuts of anything beyond.
Please mind: Pushover allows a maximum of 7500 messages per application token per month. The script provides no limiting for outgoing messages.

## TaskPaper Theme

The TaskPaper theme highlights @overdue and @prio(high) in red and bold. @Duesoon is highlighted in dark orange.
