for ((i=0;i<5;i++))
do
echo "$(python complaint.py -M 5 -I $i -T 0)" &
done
wait