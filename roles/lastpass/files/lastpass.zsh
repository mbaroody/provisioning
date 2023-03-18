# last pass show password
# example usage: lpsp amazon
lpsp () {
  fuzzy_account_name=$1
  account_id=`lpass ls | grep -i "${fuzzy_account_name}" | sed -e "s/[a-zA-Z\/()\.: ]//g" -e "s/[][]//g"`
  lpass show --password $account_id
}

# last pass show username
# example usage: lpsu amazon
lpsu () {
  fuzzy_account_name=$1
  account_id=`lpass ls | grep -i "${fuzzy_account_name}" | sed -e "s/[a-zA-Z\/()\.: ]//g" -e "s/[][]//g"`
  lpass show --username $account_id
}

