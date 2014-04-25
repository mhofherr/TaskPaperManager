TaskPaperParser
===============

TaskPaperParser (TPP) is a little python script to parse and modify a TaskPaper file.
The script is right now based on my local environment and needs some adaption for different environment.
It provides the following features:

* Move done tasks (@done) to a separate archive file
* Check any repeat-tasks (@repeat) and instantiate a new task entry if a repeat-cycle comes up
* send daily status mails for @high, @medium, @duesoon and @overdue tasks
* flag tasks with due-dates as @duesoon or @overdue (helpful for hightlighting with modified TaskPaper Theme)
* Sort the list (primary sort criterium: @prio, secondary: @start)
