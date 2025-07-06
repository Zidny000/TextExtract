import React from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from './ui/accordion';
import { Button } from './ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from './ui/card';
import { Input } from './ui/input';
import ThemeToggle from './ThemeToggle';
import { toast } from 'sonner';

const ExampleComponent = () => {
  const showToast = (type) => {
    switch (type) {
      case 'default':
        toast('This is a normal notification');
        break;
      case 'success':
        toast.success('Success! Your action was completed.');
        break;
      case 'error':
        toast.error('Error! Something went wrong.');
        break;
      case 'warning':
        toast.warning('Warning! This action might have consequences.');
        break;
      case 'info':
        toast.info('Here is some information for you.');
        break;
      default:
        toast('Hello world!');
    }
  };

  return (
    <div className="container mx-auto p-4 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">UI Components Example</h1>
        <ThemeToggle />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Button Examples</h2>
          <div className="flex flex-wrap gap-2">
            <Button>Default Button</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="link">Link</Button>
          </div>
          
          <h2 className="text-xl font-semibold mt-4">Toast Notifications</h2>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => showToast('default')}>Show Toast</Button>
            <Button onClick={() => showToast('success')} variant="outline" className="bg-green-50 text-green-600 border-green-200 hover:bg-green-100">Success Toast</Button>
            <Button onClick={() => showToast('error')} variant="outline" className="bg-red-50 text-red-600 border-red-200 hover:bg-red-100">Error Toast</Button>
            <Button onClick={() => showToast('warning')} variant="outline" className="bg-yellow-50 text-yellow-600 border-yellow-200 hover:bg-yellow-100">Warning Toast</Button>
            <Button onClick={() => showToast('info')} variant="outline" className="bg-blue-50 text-blue-600 border-blue-200 hover:bg-blue-100">Info Toast</Button>
          </div>
          
          <h2 className="text-xl font-semibold mt-4">Input Example</h2>
          <div className="space-y-2">
            <Input type="email" placeholder="Email" />
            <Input type="password" placeholder="Password" />
          </div>
        </div>
        
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Card Title</CardTitle>
              <CardDescription>Card Description with more details about this card.</CardDescription>
            </CardHeader>
            <CardContent>
              <p>This is an example card component that showcases the styling and layout options.</p>
            </CardContent>
            <CardFooter>
              <Button>Save changes</Button>
            </CardFooter>
          </Card>
        </div>
      </div>
      
      <div>
        <h2 className="text-xl font-semibold mb-4">Accordion Example</h2>
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="item-1">
            <AccordionTrigger>What is TextExtract?</AccordionTrigger>
            <AccordionContent>
              TextExtract is a tool that helps you extract text from various sources and formats.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-2">
            <AccordionTrigger>How do I use TextExtract?</AccordionTrigger>
            <AccordionContent>
              Simply select the area of the screen you want to extract text from, and TextExtract will do the rest.
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-3">
            <AccordionTrigger>Is TextExtract free to use?</AccordionTrigger>
            <AccordionContent>
              TextExtract has both free and premium options to suit your needs.
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  );
};

export default ExampleComponent;
