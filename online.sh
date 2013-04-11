#!/bin/bash
online_dir=$1
online_url=$2

play_if_big() {
	file="$1"
	while true
	do
		if [ $(stat -c%s "$file") -gt 20971520 ] || ! tmux list-panes -F '#{pane_id}' | grep -qFx "$youget_id" ; then
			if echo "$file" | grep -qF '[00].'; then
				omxplayer --loop --loop-once -o hdmi "$(echo "$file" | sed -e 's/\[[0-9][0-9]\]\./[%02d]./')" <omxin &
			else
				omxplayer -o hdmi "$file" <omxin &
			fi
			echo -n . >omxin
			break
		fi
		sleep 2
	done
}

pane_ids=`tmux list-panes -F '#{pane_id}'`
tmux split-window -hd 'you-get -n -o "'$online_dir'" "'$online_url'"'
youget_id=`tmux list-panes -F '#{pane_id}' | grep -Fxv "$pane_ids"`
touch "$online_dir/timestamp"
for i in {0..5}
do
	newfile=`find "$online_dir" -type f -newer "$online_dir/timestamp"`
	if [ -n "$newfile" ]; then
		play_if_big "$newfile"
		break
	fi
	sleep 2
done
