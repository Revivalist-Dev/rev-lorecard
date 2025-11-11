import dayjs from 'dayjs';

const formatDate = (date: string | Date): string => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss.SSS');
};

export default formatDate;
