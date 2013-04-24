#!/bin/bash
online_dir=$1
online_url=$2

play_if_big() {
	file="$1"
	while true
	do
		if [ $(stat -c%s "$file") -gt 20971520 ] || ! tmux list-panes -F '#{pane_id}' | grep -qFx "$youget_id" || (echo "$file" | grep -qF '[00].' && [ -e "${file/\[00\]\./[01].}" ]); then
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

touch "$online_dir/timestamp"
pane_ids=`tmux list-panes -F '#{pane_id}'`
tmux split-window -hd 'echo "downloading '$online_url'..."; cd "'$online_dir'"; you-get -n --no-suffix "'$online_url'" || sleep 5'
youget_id=`tmux list-panes -F '#{pane_id}' | grep -Fxv "$pane_ids"`
for i in {0..15}
do
	newfile=`find "$online_dir" -type f -newer "$online_dir/timestamp"`
	if [ -n "$newfile" ]; then
		play_if_big "$newfile"
		break
	fi
	sleep 2
done
