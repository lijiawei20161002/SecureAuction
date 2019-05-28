for ((i=0;i<5;i++))
do
echo "$(python main.py -M 5 -I $i 5 10)" &
done
wait