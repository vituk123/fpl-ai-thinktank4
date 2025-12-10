import { cn } from "@/lib/utils";
import { Text } from "@/components/retroui/Text";

const Card = ({
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        "inline-block border-2 rounded shadow-md transition-all hover:shadow-none bg-card",
        className
      )}
      {...props} />
  );
};

const CardHeader = ({
  className,
  ...props
}) => {
  return (<div className={cn("flex flex-col justify-start p-4", className)} {...props} />);
};

const CardTitle = ({
  className,
  ...props
}) => {
  return <Text as="h3" className={cn("mb-2", className)} {...props} />;
};

const CardDescription = ({
  className,
  ...props
}) => (
  <p className={cn("text-muted-foreground", className)} {...props} />
);

const CardContent = ({
  className,
  ...props
}) => {
  return <div className={cn("p-4", className)} {...props} />;
};

const CardComponent = Object.assign(Card, {
  Header: CardHeader,
  Title: CardTitle,
  Description: CardDescription,
  Content: CardContent,
});

export { CardComponent as Card };
