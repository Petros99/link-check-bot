#!/usr/bin/env python3
import csv, time, praw, re, argparse
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--test', 
        help='do not modify subreddit, just output what would be done', action='store_true')
parser.add_argument('-m', '--message',
        help='do not delete posts, just send messages to the subreddit mods', action='store_true')
parser.add_argument('-u', '--user', 
        help='the bot\'s username', type=str)
parser.add_argument('-p', '--password', 
        help='the bot\'s password', type=str)
parser.add_argument('-v', '--verbose', 
        help='enable verbose output', action='store_true')
parser.add_argument('-w', '--wait', 
        help='the number of seconds the bot waits before it checks the subreddit again', default='10', type=str)
parser.add_argument('-s', '--subreddit', 
        help='a single subreddit to run aginst', default='kikgroups', type=str)
parser.add_argument('-d', '--days', 
        help='the minimum number of days before a post is allowed of the same link', default='5', type=str)
parser.add_argument('-f', '--file', 
        help='the csv file to use as a database (use for more than one instance in the same folder)', default='database.csv', type=str)
parser.add_argument('-c', '--count',
        help='the number of posts to get each check', default='10', type=str)
parser.add_argument('-o', '--once',
        help='only do one check', action='store_true')
parser.add_argument('-a', '--agent',
        help='the user agent to use ( what the bot identifies as )', default='kikgroups link checker', type=str)
parser.add_argument('--whitelist',
        help='a comma separated list of usernames that the bot will ignore', default='', type=str)
args = parser.parse_args()

posts_count = int(args.count)
min_days = int(args.days)
sleep_seconds = int(args.wait)
sub_to_monitor = args.subreddit
bot_user = args.user
bot_pass = args.password
white_list = args.whitelist.split(',')

# todo mysql database
# todo image url

'''
csv database
optionaly mysql
for submission:
    link in database:
        user not match old_user:
            send mod post to subreddit in database with links and info
        less than x days old:
            remove post, comment that post was too recent
        else:
            overwrite old post to new post

optional
colect last subbmited dates for each user
if last_sub_date < x:
    remove submission, comment too new
else:
    overwrite last_sub_date


'''

if args.verbose: 
    def vprint(*args):  # verbose print
        print('-', *args)
else:
    def vprint(*args):  # do nothing function
        return

if args.test:
    def send_mod_message(r, message, subreddit):  #  testing function ( does not send anything )
        print()
        print('would have')
        print('mod message to', subreddit)
        print(message)
        print()

    def delete_post(r, sub, permalink, subreddit):
        print()
        print('would have')
        print('deleting', permalink)
        print()
else:
    def send_mod_message(r, message, subreddit):  #  "real" function ( should accualy send message )
        print()
        print('mod message to', subreddit)
        print(message)
        print()
        r.send_message('/r/' + sub_to_monitor, 'message from the bot', message)
        print('-----sending message-----')
        # send here

    def delete_post(r, sub, permalink, subreddit):
        print()
        print('deleting', permalink)
        print()
        r.sub.remove()
        print('------deleting-------')
        # delete here

def find_url(text):
    '''checks for http urls in text'''
    vprint('checking for url in the text')
    urls = []
    urls.extend(re.findall(r'(https?://\S+)', text)) #  http
    urls.extend(re.findall(r'(http?://\S+)', text))  #  https
    return urls

def get_row(key, db):
    ''' gets the requested row from the db '''
    vprint('getting row')
    csv_read = csv.reader(db)
    for row in csv_read:
        if row[0] == key:  # this is the key we want to retreve
            return row
    return False


def days(seconds):
    ''' convert seconds to days '''
    return (seconds / 60) / 60

r = praw.Reddit(args.agent)
# need better auth
r.login(bot_user, bot_pass ,disable_warning=True)
vprint('logged in')

# initialize stuff
update_required = False
records_to_add = []
records_to_overwrite = []

repeat = 0
while True:  # main loop
   try:
       print('-')
       try:
           db = open(args.file,'r')  # open the file
       except FileNotFoundError:
           print('warning: db file not found, creating', args.file)
           db = open(args.file, 'w') # create file
           db.close()
           db = open(args.file,'r')  # open new file for reading

       vprint('getting', posts_count, 'submissions from the subreddit')
       submissions = r.get_subreddit(sub_to_monitor).get_new(limit=posts_count)

       for sub in submissions:
           if not (sub.author in white_list) or (sub.author in (r.get_subreddit(sub_to_monitor).get_moderators())):
              vprint('now checking submission:', sub)
              urls = find_url(sub.selftext)  # get the urls out of the text
              urls.append(sub.url)
              # todo ---- url from image
              if urls != []:
                  vprint('found url(s):', urls)
                  for url in urls:
                      row = get_row(url, db)
                      if not row:  #  the url has not been posted before
                          records_to_add.append([url, sub.author, sub.created_utc, sub.permalink])
                          vprint(url, 'will be added')
                          update_required = True
                      elif sub.created_utc != float(row[2]):  # the url has been posted at a different time
                          if days(float(row[2]) - sub.created_utc) < min_days:  # the post was before the min_days limit
                              vprint(sub, 'will be deleted')
                              if not args.message:
                                  delete_post(r, sub, sub.permalink, sub_to_monitor)
                                  message = 'link repost:\n'\
                                          + '\n'\
                                          + ' old post: ' + row[3] + '\n'\
                                          + '\n'\
                                          + ' new post: ' + sub.permalink + '\n'\
                                          + '\n'\
                                          + ' old author: ' + row[1] + '\n'\
                                          + '\n'\
                                          + ' new author: ' + str(sub.author) + '\n'\
                                          + '\n'\
                                          + ' link: ' + row[0] + '\n'\
                                          + '\n'\
                                          + ' the new post has been deleted, it was posted ' + str(days(float(row[2]) - sub.created_utc)) + ' days after the original post'
                              else:
                                  message = 'link repost:\n'\
                                          + '\n'\
                                          + ' old post: ' + row[3] + '\n'\
                                          + '\n'\
                                          + ' new post: ' + sub.permalink + '\n'\
                                          + '\n'\
                                          + ' old author: ' + row[1] + '\n'\
                                          + '\n'\
                                          + ' new author: ' + str(sub.author) + '\n'\
                                          + '\n'\
                                          + ' link: ' + row[0] + '\n'\
                                          + '\n'\
                                          + ' the new post should be deleted, it was posted ' + str(days(float(row[2]) - sub.created_utc)) + ' days after the original post'


             
                          else: #  the post is later enough
                              vprint('although there is a duplicate, this submission will  not be deleted')
                              message = 'link repost:\n'\
                                      + '\n'\
                                      + ' old post: ' + row[3] + '\n'\
                                      + '\n'\
                                      + ' new post: ' + sub.permalink + '\n'\
                                      + '\n'\
                                      + ' old author: ' + row[1] + '\n'\
                                      + '\n'\
                                      + ' new author: ' + str(sub.author) + '\n'\
                                      + '\n'\
                                      + ' link: ' + row[0] + '\n'\
                                      + '\n'\
                                      + ' no action was taken, it was posted ' + str(days(float(row[2]) - sub.created_utc)) + ' days after the original post'
         
                          send_mod_message(r, message, sub_to_monitor)
                          records_to_overwrite.append([url, sub.author, sub.created_utc, sub.permalink])
                          vprint(url, 'will be overwriten')
                          update_required = True
                      else:
                         vprint('url exists')
           else:
              vprint('found no urls')
           vprint('closing db')
       db.close()
       if update_required:
          vprint('update requred')
          db = open(args.file,'a')  # append to the file
          csv_write = csv.writer(db)
          for record in records_to_add:
              vprint('writing record:', record)
              csv_write.writerow(record)
          db.close()
          db = open(args.file,'r')
          record_buffer = []
          csv_read = csv.reader(db)
          vprint('loading file into buffer')
          for record in csv_read:
              record_buffer.append(record)  # load the file into a buffer
          db.close()
          if records_to_overwrite != []:
              #  not working
              vprint('file loaded, do not close program')

              for record in records_to_overwrite:
                  for i in range(len(record_buffer)):
                      if record[0] == record_buffer[i][0]:  # this is the record that needs updating
                          record_buffer[i] = record
                          vprint('overwriting: ', record, 'with', record_buffer[i])
              
              db = open(args.file,'w')
              # overwrite the file
              csv_write = csv.writer(db)
              for record in record_buffer:
                  csv_write.writerow(record)
              db.close()
              vprint('file rewriten and saved')

          update_required = False
          records_to_add = []
          records_to_overwrite = []
       else:
          vprint('no update required')
       
       if args.once:  # were we told to run once?
          exit()

       time.sleep(sleep_seconds)
       repeat = 0
   except Exception as err:
       repeat += 1
       if repeat > 5:
            exit()
       print('ERROR', err)
       ef = open('error.txt', 'a')
       ef.write('\n')
       ef.write('error:')
       ef.write('\n')
       ef.write(str(err))
       ef.write('\n')
       ef.close()
