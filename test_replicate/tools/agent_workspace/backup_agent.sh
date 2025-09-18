#!/bin/bash
#This is a basic backup script using tar.gz
#Specify the directories to backup
directories="mindX other_projects"
#Specify the backup file name
backup_file="backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"
#Create the backup
tar -czvf "$backup_file" $directories