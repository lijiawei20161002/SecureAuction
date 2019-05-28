for ((i=0;i<3;i++))
do
echo "$(python attack.py -M 3 -I $i)" &
done
wait