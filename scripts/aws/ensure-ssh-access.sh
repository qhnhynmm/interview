#!/usr/bin/env bash
# Mở SSH (TCP 22) trong AWS Security Group cho IP hiện tại.
# Cần AWS CLI đã login:  aws login   hoặc  aws configure
#
# Usage:
#   ./scripts/aws/ensure-ssh-access.sh
#   AWS_REGION=ap-southeast-2 EC2_INSTANCE_ID=i-00e80340fe9799812 ./scripts/aws/ensure-ssh-access.sh

set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-southeast-2}"
EC2_INSTANCE_ID="${EC2_INSTANCE_ID:-i-00e80340fe9799812}"
EC2_PUBLIC_IP="${EC2_PUBLIC_IP:-54.79.17.205}"

if ! command -v aws >/dev/null 2>&1; then
  echo "Cần AWS CLI. Cài: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
  exit 1
fi

MY_IP="$(curl -fsSL https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]')"
if [[ -z "$MY_IP" ]]; then
  echo "Không lấy được public IP."
  exit 1
fi

echo "=== Mở SSH cho IP: ${MY_IP}/32 ==="
echo "Region: ${AWS_REGION}"
echo "Instance: ${EC2_INSTANCE_ID}"

SG_ID="$(aws ec2 describe-instances \
  --region "$AWS_REGION" \
  --instance-ids "$EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)"

if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
  echo "Không tìm thấy Security Group cho instance ${EC2_INSTANCE_ID}"
  exit 1
fi

echo "Security Group: ${SG_ID}"

# Thêm rule SSH (idempotent: bỏ qua nếu đã có)
if aws ec2 authorize-security-group-ingress \
  --region "$AWS_REGION" \
  --group-id "$SG_ID" \
  --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=${MY_IP}/32,Description=Aurelia-deploy-SSH}]" \
  2>/dev/null; then
  echo "Đã thêm rule SSH cho ${MY_IP}/32"
else
  echo "Rule SSH cho ${MY_IP}/32 có thể đã tồn tại — tiếp tục."
fi

echo ""
echo "Thử SSH:"
echo "  ssh -i ~/Downloads/aurelia_key.pem ubuntu@${EC2_PUBLIC_IP}"