for port in {5441..5445}; do
    PGPORT=$port py.test -vv -s
done

