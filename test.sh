for ((i=0;i<3;i++))
do
echo "$(python main.py -M 3 -T 0 -I $i 5 10)" &
done
wait