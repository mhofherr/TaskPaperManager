# TaskPaperParser


TaskPaperParser (TPP) is a little python script to parse and modify a TaskPaper file.
The script is right now based on my local environment and needs some adaption for different environment.
It provides the following features:

* Move done tasks (@done) to a separate archive file
* Check any repeat-tasks (@repeat) and instantiate a new task entry if a repeat-cycle comes up
* send daily status mails for @high, @medium, @duesoon and @overdue tasks
* flag tasks with due-dates as @duesoon or @overdue (helpful for hightlighting with modified TaskPaper Theme)
* Sort the list (primary sort criterium: @prio, secondary: @start)
* Copy tasks with the tag @maybe in a dedicated maybe list and remove from master list

The variable parameters are configured via a separate config file (tpp.cfg):

    [tpp]
    debug: False
    duedelta: days
    dueinterval: 3

    [mail]
    encryptmail: True
    gnupghome: <Path to your home>/.gnupg
    targetfingerprint: <Fingerprint of the gpg key of the email receiver>
    sendmail: True
    smtpserver = <FQDN of your smtp server>
    smtpport = <listening port of your smtp server>
    smtpuser = <your user on the server>
    smtppassword = <your password>
    sourceemail: <sender mail address>
    destworkemail: <receiver mail address; work>
    desthomeemail: <receiver mail address; home>

*dueinterval:* all tasks will be tagged as @duesoon when today is x days (or whatever you define for *duedelta*) before the duedate (defined in @due(...))

## Sending email
You can either send email encrypted (gpg) or in plain text. The communication to the server uses SSL/TLS with starttls. Content encryption requires gnupg installed and the python-gnupg module.

## Sending pushover messages

## TaskPaper Theme

The TaskPaper theme highlights @overdue and @prio(high) in red and bold. @Duesoon is highlighted in dark orange.
