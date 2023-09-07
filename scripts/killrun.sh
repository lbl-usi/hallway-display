kill -9 `ps ux | grep 'update.sh' | grep -v 'grep' | awk {'print $2'}`
kill -9 `ps ux | grep 'vue' | grep -v 'grep' | awk {'print $2'}`
rm -f ___*
